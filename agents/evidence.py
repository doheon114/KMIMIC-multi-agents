"""Evidence RAG 에이전트: 근거 문헌(RAG 팀) + 유사 환자(유사환자 팀)를 한 노드에서 병렬 대기 없이 호출.

실제 구현은 rag/pipeline.py, similarity/ 뒤에 숨어 있다. 여기는 결과를 화면용으로 정리만 한다.
"""
from __future__ import annotations

from data.schema import AgentFinding, Patient
from rag.pipeline import retrieve_evidence
from similarity.base import get_similar_finder


def evidence_rag(state):
    p, d = Patient(**state["patient"]), state["derived"]
    ev = retrieve_evidence(d["response"]["grade"], d["flags"], k=3)
    docs = ev["docs"]
    try:
        sims = get_similar_finder().find(p, k=5)
    except Exception:  # noqa: BLE001  팀 코드 오류가 나도 나머지 분석은 계속
        sims = []
    improved = sum(s.outcome == "반응 개선" for s in sims)
    bullets = [f"유사 환자 {len(sims)}명 중 {improved}명 반응 개선" if sims else "유사 환자 검색 실패",
               f"근거 문헌 {len(docs)}건 ({'RAG' if ev['route'] == 'primary' else '내장 가이드라인'})"]
    return {"findings": {"Evidence RAG": AgentFinding(
                agent="Evidence RAG", bullets=bullets,
                data={"improved": improved, "n": len(sims), "query": ev["query"], "route": ev["route"]}).model_dump()},
            "evidence": [x.model_dump() for x in docs],
            "similar": [x.model_dump() for x in sims]}
