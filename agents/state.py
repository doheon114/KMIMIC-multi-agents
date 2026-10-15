from typing import Any, TypedDict

class AgentState(TypedDict, total=False):
    patient: dict[str, Any]
    cardiology: dict[str, Any]
    nephrology: dict[str, Any]
    pharmacy: dict[str, Any]
    evidence: dict[str, Any]
    similar_patients: list[dict[str, Any]]
    similarity_error: str
    safety: dict[str, Any]
    final: dict[str, Any]
    precheck_missing: list[str]
    skip_analysis: bool
    chief_summary: str
    chief_used: bool