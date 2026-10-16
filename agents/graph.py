import json
from langgraph.graph import StateGraph, START, END
from agents.state import AgentState
from agents.safety import validate_safety
from agents.pharmacy_agent import run_pharmacy_agent
from data.schemas import PatientInput, SpecialistResult, EvidenceResult, SimilarPatient, SafetyResult, FinalReport, ModelInfo
from llm.factory import LLMClient
from rag.adapter import EvidenceAdapter
from similarity.adapter import SimilarityAdapter
from tools.clinical_tools import missing_key_fields
from tools.integration_tools import make_evidence_tool, make_similarity_tool

ESSENTIAL = {"sbp", "heart_rate", "creatinine", "sodium", "potassium", "furosemide_dose_mg", "urine_output_6h_ml"}
BRANCHES = ("cardiology", "nephrology", "pharmacy", "evidence", "similarity")

def build_graph(mini: LLMClient, chief: LLMClient, rag: EvidenceAdapter, similarity: SimilarityAdapter):
    builder = StateGraph(AgentState)
    evidence_tool = make_evidence_tool(rag)
    similarity_tool = make_similarity_tool(similarity)

    def precheck(state):
        missing = missing_key_fields(PatientInput.model_validate(state["patient"]))
        return {"precheck_missing": missing, "skip_analysis": len(ESSENTIAL.intersection(missing)) >= 3} # missing at least three!

    def abstain(state):
        patient = PatientInput.model_validate(state["patient"])
        reason = "At least three essential fields missing; analysis skipped before model/tool calls."
        draft = f"[HF-PathGuard DEMO] Patient {patient.patient_id}: INSUFFICIENT_DATA. Clinical review required. No message has been sent."
        specialists = {kind: SpecialistResult(agent=kind, assessment="Not run: insufficient data", reason=reason)
                       for kind in ("cardiology", "nephrology", "pharmacy")}
        report = FinalReport(patient_id=patient.patient_id, **specialists, evidence=EvidenceResult(),
            overall_status="INSUFFICIENT_DATA", review_reasons=[reason],
            missing_fields=state["precheck_missing"],
            final_summary="Insufficient essential patient data. No AI analysis was run.",
            notification_draft=draft, model_info=ModelInfo(provider="none", model_name="precheck-only"))
        return {"final": report.model_dump(mode="json")}

    def specialist_node(kind):
        def run(state):
            patient = PatientInput.model_validate(state["patient"])
            if kind == "pharmacy":  # the one tool-calling agent; output schema is unchanged
                result, called = run_pharmacy_agent(mini, patient)
                return {"pharmacy": result.model_dump(mode="json"), "pharmacy_tool_calls": called}
            return {kind: mini.specialist(kind, patient).model_dump(mode="json")}
        return run

    def evidence_node(state):
        query = "Find evidence relevant to acute HF early diuretic response and renal/electrolyte safety; return sources."
        try:
            return {"evidence": evidence_tool.invoke({"question": query})}
        except Exception as exc:
            return {"evidence": EvidenceResult(refused=True, error=f"Evidence tool failed ({type(exc).__name__})").model_dump(mode="json")}

    def similarity_node(state):
        patient = PatientInput.model_validate(state["patient"])
        try:
            return {"similar_patients": similarity_tool.invoke({"patient_json": patient.model_dump(mode="json"), "top_k": 5})}
        except Exception as exc:
            return {"similar_patients": [], "similarity_error": type(exc).__name__}

    def safety_node(state):
        patient = PatientInput.model_validate(state["patient"])
        specialists = [SpecialistResult.model_validate(state[k]) for k in ("cardiology", "nephrology", "pharmacy")]
        evidence = EvidenceResult.model_validate(state["evidence"])
        result = validate_safety(patient, specialists, evidence, state.get("similarity_error", ""))
        return {"safety": result.model_dump(mode="json")}

    def mini_safety(state):
        patient = PatientInput.model_validate(state["patient"])
        safety = SafetyResult.model_validate(state["safety"])
        audit = mini.safety_audit(patient, safety.overall_status, safety.review_reasons)
        # Mini may add warnings but cannot remove any deterministic warning.
        if audit.needs_review:
            safety.review_reasons.append(f"Mini safety audit: {audit.reason}")
            if safety.overall_status == "OK":
                safety.overall_status = "REVIEW"
        return {"safety": safety.model_dump(mode="json")}

    def chief_node(state):
        patient = PatientInput.model_validate(state["patient"])
        safety = SafetyResult.model_validate(state["safety"])
        fallback = (f"{patient.patient_id}: {safety.overall_status}. Uncertainties require clinician review. "
                    "Do not infer missing data or use this output for treatment decisions.")
        if chief.is_mock:
            return {"chief_summary": fallback, "chief_used": False}
        payload = {"patient_id": patient.patient_id, "safety_status": safety.overall_status,
                   "review_reasons": safety.review_reasons,
                   "specialists": {k: state[k]["assessment"] for k in ("cardiology", "nephrology", "pharmacy")},
                   "evidence_summary": state["evidence"].get("summary", "")}
        try:
            summary = chief.text(
                "Write a cautious clinician-facing summary under 80 words. No diagnosis, dosing, treatment, "
                "invented citations, or assurance; never change the safety status.",
                json.dumps(payload, ensure_ascii=False)).strip()
            return {"chief_summary": summary or fallback, "chief_used": bool(summary)}
        except Exception:
            return {"chief_summary": fallback, "chief_used": False}

# Simple node for "OK" >> we should revise the comment.
    def simple_node(state):
        return {"chief_summary": "No automatic review flags in this prototype. "
                                 "Clinical validation is still required; Chief LLM skipped.",
                "chief_used": False}

    def final_node(state):
        patient = PatientInput.model_validate(state["patient"])
        safety = SafetyResult.model_validate(state["safety"])
        specialists = {kind: SpecialistResult.model_validate(state[kind])
                       for kind in ("cardiology", "nephrology", "pharmacy")}
        model = chief if state["chief_used"] else mini
        report = FinalReport(patient_id=patient.patient_id, **specialists,
            evidence=EvidenceResult.model_validate(state["evidence"]),
            similar_patients=[SimilarPatient.model_validate(r) for r in state.get("similar_patients", [])],
            overall_status=safety.overall_status, review_reasons=safety.review_reasons,
            missing_fields=safety.missing_fields, final_summary=state["chief_summary"],
            notification_draft=safety.notification_draft,
            model_info=ModelInfo(provider=model.provider, model_name=model.model_name),
            is_demo=mini.is_mock and chief.is_mock)
        return {"final": report.model_dump(mode="json")}

# Add nodes
    builder.add_node("precheck", precheck)
    builder.add_node("dispatch", lambda state: {})
    builder.add_node("abstain", abstain)
    for kind in ("cardiology", "nephrology", "pharmacy"):
        builder.add_node(kind, specialist_node(kind))
    builder.add_node("evidence", evidence_node)
    builder.add_node("similarity", similarity_node)
    builder.add_node("safety", safety_node)
    builder.add_node("mini_safety", mini_safety)
    builder.add_node("chief", chief_node)
    builder.add_node("simple", simple_node)
    builder.add_node("final", final_node)
    builder.add_edge(START, "precheck")

    builder.add_conditional_edges("precheck", lambda state: "abstain" if state["skip_analysis"] else "dispatch",
                                  {"abstain": "abstain", "dispatch": "dispatch"})
    
    builder.add_edge("abstain", END)

# fan-out
    for branch in BRANCHES:
        builder.add_edge("dispatch", branch)
# fan-in
    builder.add_edge(list(BRANCHES), "safety")
    builder.add_edge("safety", "mini_safety")

# Important part   
    builder.add_conditional_edges("mini_safety", lambda state: "chief" if state["safety"]["overall_status"] != "OK" else "simple",
                                  {"chief": "chief", "simple": "simple"})
    
    builder.add_edge("chief", "final")
    builder.add_edge("simple", "final")
    builder.add_edge("final", END)

    return builder.compile()
