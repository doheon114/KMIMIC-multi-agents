"""에이전트가 부르는 근거 검색 파이프라인. 강의 꿀팁 세 가지를 묶었다.

1) 질의 재작성 (RAG 3.6 키워드 사전): 검사 flag/약어를 문서에 실제로 나오는 용어로 바꾼다.
   "직장인 → 거주자" 처럼, "AKI" → "acute kidney injury creatinine" 식으로 어휘 불일치를 줄인다.
2) 관련성 검사 (LangGraph 2.3 Agentic RAG / 2.4 Self-RAG): 가져온 문서가 질문과 관련 있는지 거른다.
   LLM이 있으면 LLM 채점, 없으면 통과.
3) 교정 fallback (LangGraph 2.5 Corrective RAG): 관련 문서가 하나도 없으면 웹 검색 대신
   내장 가이드라인 세트로 대체한다 (임상에서는 출처 불명 웹 결과보다 검증된 문서가 안전).
"""
from __future__ import annotations

from data.schema import EvidenceDoc
from llm import get_llm

from .base import get_retriever
from .mock_retriever import MockEvidenceRetriever

# 키워드 사전: 왼쪽은 내부 flag/약어, 오른쪽은 문서에 나오는 표현. RAG 팀 문서에 맞춰 늘린다.
KEYWORD_DICT = {
    "poor": "poor diuretic response resistance",
    "borderline": "insufficient diuretic response",
    "aki": "acute kidney injury creatinine renal",
    "egfr_lt30": "renal impairment egfr",
    "hyperkalemia": "hyperkalemia potassium mra raas",
    "hypokalemia": "hypokalemia potassium",
    "hyponatremia_mod": "hyponatremia sodium",
    "hypotension": "hypotension low blood pressure",
    "nsaid": "nsaid diuretic resistance renal",
    "raas_hyperk": "hyperkalemia mra raas",
}


def build_query(grade: str, flags: list[str]) -> str:
    return " ".join(["diuretic response", grade.lower(), *[f.lower() for f in flags]])


def rewrite_query(query: str) -> str:
    words = query.split()
    return " ".join(KEYWORD_DICT.get(w, w) for w in words)


GRADE_PROMPT = (
    "다음 문서가 급성 심부전 환자 질문에 관련 있으면 yes, 아니면 no 로만 답하세요.\n"
    "질문: {query}\n문서: {doc}"
)


def grade(query: str, docs: list[EvidenceDoc]) -> list[EvidenceDoc]:
    llm = get_llm()
    if llm is None:
        return docs
    kept = []
    for d in docs:
        try:
            ans = llm.invoke(GRADE_PROMPT.format(query=query, doc=f"{d.title}: {d.snippet}")).content
            if "yes" in ans.lower():
                kept.append(d)
        except Exception:  # noqa: BLE001  채점 실패 시 문서를 버리지 않는다
            kept.append(d)
    return kept


def retrieve_evidence(grade_label: str, flags: list[str], k: int = 3) -> dict:
    query = rewrite_query(build_query(grade_label, flags))
    route = "primary"
    try:
        docs = grade(query, get_retriever().search(query, k=k))
    except Exception:  # noqa: BLE001  RAG 팀 서버가 죽어도 시연은 계속
        docs = []
    if not docs:
        route = "fallback"
        docs = MockEvidenceRetriever().search(query, k=k)
    return {"query": query, "route": route, "docs": docs}
