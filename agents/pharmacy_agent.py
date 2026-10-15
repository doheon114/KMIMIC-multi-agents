"""Pharmacy specialist as a small tool-calling agent (the one 'agent' inside the fixed workflow).

The graph route stays fixed. Inside this node the model decides which rule-based
tools to call (max MAX_ROUNDS rounds), then returns the usual SpecialistResult JSON.
Safety: tool flags are deterministic and can only ADD review; any model/parse
failure falls back to the plain (non-tool) specialist call.
"""
import json
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from data.schemas import PatientInput, SpecialistResult
from llm.factory import LLMClient, _json_object, mock_specialist, normalize_specialist
from tools.clinical_tools import clinical_features
from tools.pharmacy_tools import make_pharmacy_tools

MAX_ROUNDS = 3
SYSTEM = (
    "You are the pharmacy reviewer in an unvalidated clinical research demonstration. "
    "You have tools: check_drug_interactions, check_renal_dosing, check_electrolytes. "
    "Call only the tools you need (they take no arguments and read the patient record themselves). "
    "Do not prescribe, change doses, or infer missing values. "
    "When done, return ONLY JSON with agent, assessment, concern_level (low/moderate/high/unknown), "
    "confidence (low/moderate/high/unknown), needs_review (boolean), reason (string)."
)
FINALIZE = "Tool budget reached. Do not call more tools; return the final JSON now."


class ScriptedPharmacyModel:
    """Deterministic stand-in for LLM_PROVIDER=mock: picks tools by simple rules, then answers."""
    def __init__(self, patient: PatientInput):
        self.patient = patient

    def invoke(self, messages, tools=True) -> AIMessage:
        if tools and not any(isinstance(m, ToolMessage) for m in messages):
            p, calls = self.patient, []
            if p.medication_history:
                calls.append("check_drug_interactions")
            if p.creatinine is not None:
                calls.append("check_renal_dosing")
            if p.potassium is not None or p.sodium is not None:
                calls.append("check_electrolytes")
            if calls:
                return AIMessage(content="", tool_calls=[
                    {"name": n, "args": {}, "id": f"mock-{i}", "type": "tool_call"} for i, n in enumerate(calls)])
        return AIMessage(content=mock_specialist("pharmacy", self.patient).model_dump_json())


def run_pharmacy_agent(mini: LLMClient, patient: PatientInput) -> tuple[SpecialistResult, list[str]]:
    tools = make_pharmacy_tools(patient)
    by_name = {t.name: t for t in tools}
    model = ScriptedPharmacyModel(patient) if mini.is_mock else None
    invoke = model.invoke if model else (lambda msgs, tools_on=True: mini.chat(msgs, tools if tools_on else None))
    messages = [SystemMessage(content=SYSTEM), HumanMessage(content=json.dumps(
        {"patient": patient.model_dump(mode="json"), "observations": clinical_features(patient)}, ensure_ascii=False))]
    called, findings = [], []
    try:
        for _ in range(MAX_ROUNDS):
            answer = invoke(messages, True)
            messages.append(answer)
            if not answer.tool_calls:
                break
            for call in answer.tool_calls:
                tool = by_name.get(call["name"])
                output = tool.invoke({}) if tool else {"error": f"unknown tool {call['name']}"}
                called.append(call["name"])
                findings.extend(output.get("flags", []))
                messages.append(ToolMessage(content=json.dumps(output, ensure_ascii=False), tool_call_id=call["id"]))
        else:
            # Still asking for tools after MAX_ROUNDS: force a final answer without tools.
            messages.append(HumanMessage(content=FINALIZE))
            answer = invoke(messages, False)
        result = normalize_specialist("pharmacy", _json_object(str(answer.content)))
    except Exception:
        result = mini.specialist("pharmacy", patient)  # previous non-tool behaviour
    return merge_tool_findings(result, called, findings), called


def merge_tool_findings(result: SpecialistResult, called: list[str], findings: list[str]) -> SpecialistResult:
    """Tool flags can only escalate: the model cannot clear a deterministic finding."""
    unique = list(dict.fromkeys(findings))
    if unique:
        result.needs_review = True
        if result.concern_level in {"low", "unknown"}:
            result.concern_level = "moderate"
        if result.assessment == "No flag in synthetic review":
            result.assessment = "Concern noted"
        result.reason += " Tool findings: " + "; ".join(unique) + "."
    result.reason += f" Tools used: {', '.join(dict.fromkeys(called)) or 'none'}."
    return result
