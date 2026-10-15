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
    def __init__(self, settings: Settings):
        self.settings = settings
        self._limiter = threading.BoundedSemaphore(settings.llm_max_concurrent_calls)
        self._model = None
        self._specialist_chain = None
        if settings.llm_provider == "openai_compatible":
            settings.require_remote_authorization()
            if not settings.llm_base_url or not settings.llm_model:
                raise ValueError("LLM_BASE_URL and LLM_MODEL are required")
            from langchain_openai import ChatOpenAI
            self._model = ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.llm_api_key or "unused-if-no-auth",
                base_url=settings.llm_base_url,
                temperature=0,
                timeout=settings.llm_timeout_seconds,
                max_retries=0,
            )
            # Same LCEL structure as the LangChain lessons:
            # ChatPromptTemplate | LLM | StrOutputParser.
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            prompt = ChatPromptTemplate.from_messages([
                ("system", "{instructions}"),
                ("human", "{patient_data}"),
            ])
            self._specialist_chain = prompt | self._model | StrOutputParser()
        elif settings.llm_provider != "mock":
            raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

    @property
    def is_mock(self) -> bool:
        return self._model is None

    def text(self, system: str, user: str) -> str:
        if self._model is None:
            return "Mock language model; no remote inference was performed."
        from langchain_core.messages import SystemMessage, HumanMessage
        with self._limiter:
            result = self._model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
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
            result = SpecialistResult.model_validate(_json_object(raw_answer))
            if result.agent != kind:
                raise ValueError("Agent label mismatch")
            return result
        except Exception as exc:
            return SpecialistResult(agent=kind, assessment="LLM output unavailable", needs_review=True,
                reason=f"Inference or schema validation failed ({type(exc).__name__}); clinician review required.")


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
    return SpecialistResult(agent=kind, assessment="Data review required (synthetic example)",
        concern_level="unknown", confidence="unknown", needs_review=True, reason=reason)
