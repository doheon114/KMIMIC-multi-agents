"""Model adapter shared across specialists and baseline.

Uses plain JSON prompts for API compatibility; the validated schema is enforced
locally even when a provider lacks function calling or structured-output mode.
"""
import json
import re
import threading
from typing import Any

from config.settings import Settings
from data.schemas import PatientInput, SpecialistResult
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

class SafetyAudit(BaseModel):
    needs_review: bool = True
    reason: str = Field(min_length=1, max_length=400)
from tools.clinical_tools import clinical_features, urine_output_per_hour


def _json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Model must return a JSON object")
    return parsed


class LLMClient:
    def __init__(self, settings: Settings, tier: str = "chief"):
        self.settings = settings
        if tier not in {"chief", "mini"}:
            raise ValueError(f"Unknown model tier: {tier}")
        self.tier = tier
        self.provider = settings.mini_llm_provider if tier == "mini" else settings.llm_provider
        self.model_name = settings.mini_llm_model if tier == "mini" else settings.llm_model
        base_url = settings.mini_llm_base_url if tier == "mini" else settings.llm_base_url
        api_key = settings.mini_llm_api_key if tier == "mini" else settings.llm_api_key
        self._limiter = threading.BoundedSemaphore(settings.llm_max_concurrent_calls)
        self._usage_lock = threading.Lock()
        self._usage_input = 0
        self._usage_output = 0
        self._usage_missing = False
        self._requests = 0
        self._model = None
        self._specialist_chain = None
        if self.provider == "openai_compatible":
            settings.require_remote_authorization()
            if not base_url or not self.model_name:
                raise ValueError(f"{tier} LLM base URL and model are required")
            from langchain_openai import ChatOpenAI
            self._model = ChatOpenAI(
                model=self.model_name,
                api_key=api_key or "unused-if-no-auth",
                base_url=base_url,
                temperature=0,
                timeout=settings.llm_timeout_seconds,
                max_retries=0,
            )
            # Same LCEL structure as the LangChain lessons:
            # ChatPromptTemplate | LLM | StrOutputParser.
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([
                ("system", "{instructions}"),
                ("human", "{patient_data}"),
            ])
            # Preserve AIMessage usage metadata (a string parser discards it).
            self._specialist_chain = prompt | self._model
        elif self.provider != "mock":
            raise ValueError(f"Unsupported {tier} LLM provider: {self.provider}")

    @property
    def is_mock(self) -> bool:
        return self._model is None

    def _record_usage(self, message) -> None:
        metadata = getattr(message, "usage_metadata", None) or {}
        response = getattr(message, "response_metadata", None) or {}
        fallback = response.get("token_usage", {}) or {}
        input_tokens = metadata.get("input_tokens", fallback.get("prompt_tokens"))
        output_tokens = metadata.get("output_tokens", fallback.get("completion_tokens"))
        with self._usage_lock:
            self._requests += 1
            if input_tokens is None or output_tokens is None:
                self._usage_missing = True
            else:
                self._usage_input += int(input_tokens)
                self._usage_output += int(output_tokens)

    def usage_snapshot(self) -> dict:
        with self._usage_lock:
            complete = self._requests > 0 and not self._usage_missing
            return {"calls": self._requests, "input_tokens": self._usage_input if complete else None,
                    "output_tokens": self._usage_output if complete else None,
                    "total_tokens": self._usage_input + self._usage_output if complete else None}

    def text(self, system: str, user: str) -> str:
        if self._model is None:
            return "Mock language model; no remote inference was performed."
        with self._limiter:
            result = self._model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        self._record_usage(result)
        return str(result.content)

    def specialist(self, kind: str, patient: PatientInput) -> SpecialistResult:
        if self.is_mock:
            return mock_specialist(kind, patient)
        system = (
            f"You are the {kind} reviewer in an unvalidated clinical research demonstration. "
            "Do not prescribe, diagnose conclusively, or infer missing values. "
            "State observational concerns only; flag incomplete information and request clinician review. "
            "Return ONLY JSON with agent, assessment, concern_level (low/moderate/high/unknown), "
            "confidence (low/moderate/high/unknown), needs_review (boolean), reason (string)."
        )
        user = json.dumps({"patient":patient.model_dump(mode="json"), "observations":clinical_features(patient)}, ensure_ascii=False)
        try:
            with self._limiter:
                raw_answer = self._specialist_chain.invoke({
                    "instructions": system,
                    "patient_data": user,
                })
            self._record_usage(raw_answer)
            data = _json_object(str(raw_answer.content))
            data["agent"] = kind  # 라벨은 코드가 정함 (모델이 "Cardiology"라고 써도 통과)
            for key in ("concern_level", "confidence"):
                value = str(data.get(key, "unknown")).strip().lower()
                value = {"medium": "moderate"}.get(value, value)
                data[key] = value if value in {"low", "moderate", "high"} else "unknown"
            return SpecialistResult.model_validate(data)
        except Exception as exc:
            return SpecialistResult(agent=kind, assessment="LLM output unavailable", needs_review=True,
                reason=f"Inference or schema validation failed ({type(exc).__name__}); clinician review required.")

    def safety_audit(self, patient: PatientInput, rule_status: str, rule_reasons: list[str]) -> SafetyAudit:
        """An advisory Mini chain; its result may escalate but never clear rule warnings."""
        if self.is_mock:
            return SafetyAudit(needs_review=False, reason="Mock audit; deterministic rules remain authoritative")
        system = (
            "You are a conservative data-quality reviewer for a synthetic clinical demo. "
            "Do not prescribe or infer missing values. Find additional uncertainty, never cancel rule warnings. "
            "Return ONLY JSON: {\"needs_review\": boolean, \"reason\": \"short explanation\"}."
        )
        payload = {"patient": patient.model_dump(mode="json"), "rule_status": rule_status,
                   "rule_reasons": rule_reasons}
        try:
            return SafetyAudit.model_validate(_json_object(self.text(system, json.dumps(payload))))
        except Exception as exc:
            return SafetyAudit(needs_review=True, reason=f"Mini safety audit unavailable ({type(exc).__name__})")


def mock_specialist(kind: str, patient: PatientInput) -> SpecialistResult:
    if kind == "cardiology":
        per_hour = urine_output_per_hour(patient)
        observation = "6-hour urine output unavailable" if per_hour is None else f"Recorded 6-hour urine output: {patient.urine_output_6h_ml:g} mL ({per_hour:g} mL/h)"
        reason = observation + "; dose-to-measurement timing and clinical context are not established."
    elif kind == "nephrology":
        reason = f"Creatinine: {patient.creatinine} mg/dL; baseline: {patient.baseline_creatinine if patient.baseline_creatinine is not None else 'missing'}; longitudinal trajectory not established."
    elif kind == "pharmacy":
        reason = f"Recorded furosemide: {patient.furosemide_dose_mg} mg; full medication history: {'available' if patient.medication_history else 'missing'}."
    else:
        raise ValueError(f"Unknown specialist: {kind}")
    per_hour = urine_output_per_hour(patient)
    flags = {"cardiology": per_hour is not None and per_hour < 100,
             "nephrology": patient.baseline_creatinine is None or (patient.creatinine or 0) - patient.baseline_creatinine >= 0.3,
             "pharmacy": not patient.medication_history}
    return SpecialistResult(agent=kind, assessment="Concern noted" if flags[kind] else "No flag in synthetic review",
        concern_level="moderate" if flags[kind] else "low", confidence="low",
        needs_review=flags[kind], reason=reason)
