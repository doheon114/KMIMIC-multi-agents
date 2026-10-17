"""LangChain @tool facades over replaceable, testable integration adapters.

Keep HTTP details and similarity algorithms outside the LangGraph specialist nodes.
"""
from langchain_core.tools import tool
from rag.adapter import EvidenceAdapter
from similarity.adapter import SimilarityAdapter
from data.schemas import PatientInput

def make_evidence_tool(adapter: EvidenceAdapter):
    @tool
    def evidence_search(question: str) -> dict:
        """Retrieve clinical literature from the team's evidence-RAG service."""
        return adapter.ask(question).model_dump(mode="json")
    return evidence_search

def make_similarity_tool(adapter: SimilarityAdapter):
    @tool
    def similar_patient_search(patient_json: dict, top_k: int = 5) -> list[dict]:
        """Look up similar cases with a separate approved model (no treatment inference)."""
        patient = PatientInput.model_validate(patient_json)
        return [p.model_dump(mode="json") for p in adapter.find(patient, top_k)]
    return similar_patient_search
