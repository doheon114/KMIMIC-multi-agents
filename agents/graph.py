"""Five parallel read-only branches converge on deterministic safety and report synthesis."""
from langgraph.graph import StateGraph, START, END

from agents.state import AgentState
from agents.safety import validate_safety
from data.schemas import (PatientInput, SpecialistResult, EvidenceResult, SimilarPatient,
                          SafetyResult, FinalReport, ModelInfo)
from llm.factory import LLMClient
from rag.adapter import EvidenceAdapter
from similarity.adapter import SimilarityAdapter
from tools.integration_tools import make_evidence_tool, make_similarity_tool

def build_graph(llm: LLMClient, rag: EvidenceAdapter, similarity: SimilarityAdapter):
    graph_builder = StateGraph(AgentState)
    evidence_tool = make_evidence_tool(rag)
    similarity_tool = make_similarity_tool(similarity)

    def specialist_node(kind: str):
        def run(state: AgentState) -> dict:
            patient = PatientInput.model_validate(state["patient"])
            return {kind: llm.specialist(kind, patient).model_dump(mode="json")}
        return run

    def evidence_node(state: AgentState) -> dict:
        patient = PatientInput.model_validate(state["patient"])
        # Only a short need-to-know question is sent; no full medical note by default.
        query = "Find evidence relevant to acute HF early diuretic response and renal/electrolyte safety; return sources."
        try:
            return {"evidence": evidence_tool.invoke({"question": query})}
        except Exception as exc:
            evidence = EvidenceResult(refused=True, error=f"Evidence tool failed ({type(exc).__name__})")
            return {"evidence": evidence.model_dump(mode="json")}

    def similarity_node(state: AgentState) -> dict:
        patient = PatientInput.model_validate(state["patient"])
        try:
            results = similarity_tool.invoke({"patient_json": patient.model_dump(mode="json"), "top_k": 5})
            return {"similar_patients": results}
        except Exception as exc:
            return {"similar_patients": [], "similarity_error": type(exc).__name__}

    def safety_node(state: AgentState) -> dict:
        patient = PatientInput.model_validate(state["patient"])
        agents = [SpecialistResult.model_validate(state[k]) for k in ("cardiology", "nephrology", "pharmacy")]
        evidence = EvidenceResult.model_validate(state["evidence"])
        safety = validate_safety(patient, agents, evidence, state.get("similarity_error", ""))
        return {"safety": safety.model_dump(mode="json")}

    def final_node(state: AgentState) -> dict:
        patient = PatientInput.model_validate(state["patient"])
        safety = SafetyResult.model_validate(state["safety"])
        specialists = {kind:SpecialistResult.model_validate(state[kind]) for kind in ("cardiology","nephrology","pharmacy")}
        summary = (
            f"{patient.patient_id}: {safety.overall_status}. "
            "Specialist observations are preliminary and require clinician review. "
            "Unknown baseline/treatment timing must not be inferred."
        )
        report = FinalReport(patient_id=patient.patient_id, **specialists,
            evidence=EvidenceResult.model_validate(state["evidence"]),
            similar_patients=[SimilarPatient.model_validate(r) for r in state.get("similar_patients", [])],
            overall_status=safety.overall_status, review_reasons=safety.review_reasons,
            missing_fields=safety.missing_fields, final_summary=summary,
            notification_draft=safety.notification_draft,
            model_info=ModelInfo(provider=llm.settings.llm_provider, model_name=llm.settings.llm_model),
            is_demo=llm.is_mock)
        return {"final": report.model_dump(mode="json")}

    for kind in ("cardiology", "nephrology", "pharmacy"):
        graph_builder.add_node(kind, specialist_node(kind))
    graph_builder.add_node("evidence", evidence_node)
    graph_builder.add_node("similarity", similarity_node)
    graph_builder.add_node("safety", safety_node)
    graph_builder.add_node("final", final_node)
    branches = ("cardiology", "nephrology", "pharmacy", "evidence", "similarity")
    for branch in branches:
        graph_builder.add_edge(START, branch)
    # A joined edge guarantees all specialist/tool branches finish before review.
    graph_builder.add_edge(list(branches), "safety")
    graph_builder.add_edge("safety", "final")
    graph_builder.add_edge("final", END)
    return graph_builder.compile()
