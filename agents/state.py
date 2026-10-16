from typing import Any, TypedDict

class AgentState(TypedDict, total=False):
    patient: dict[str, Any]
    cardiology: dict[str, Any]
    nephrology: dict[str, Any]
    pharmacy: dict[str, Any]
    pharmacy_tool_calls: list[str]
    evidence: dict[str, Any]
    similar_patients: list[dict[str, Any]]
    similarity_error: str
    safety: dict[str, Any]
    final: dict[str, Any]
    precheck_missing: list[str]
    skip_analysis: bool
    chief_summary: str
    chief_used: bool

# total=False 의미: 모든 필드가 첫 시작부터 다 있을 필요는 없다.