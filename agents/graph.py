"""HF-PathGuard 멀티 에이전트 그래프.

    START → intake ─┬─ cardiology ─────┐
                    ├─ nephrology ─────┤
                    ├─ pharmacy ───────┼─→ chief → safety ─┬─(알림 필요)→ human_review ─(승인)→ notify → END
                    ├─ evidence_rag ───┤                   └─(정상)────────────────────────────────→ END
                    └─ nurse_feedback ─┘

- 병렬 fan-out / fan-in: 강의 2.7
- Supervisor(Chief): 강의 2.8, 3.7
- human-in-the-loop (interrupt + Command + checkpointer): 강의 3.6, 3.5
  MemorySaver 는 서버 재시작 시 사라진다. 유지하려면 langgraph-checkpoint-sqlite 의 SqliteSaver 로 교체.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from . import specialists
from .chief import chief
from .evidence import evidence_rag
from .safety import human_review, notify, route_after_safety, safety
from .state import PGState

SPECIALISTS = ["cardiology", "nephrology", "pharmacy", "evidence_rag", "nurse_feedback"]


def build_graph(checkpointer=None):
    g = StateGraph(PGState)
    g.add_node("intake", specialists.intake)
    g.add_node("cardiology", specialists.cardiology)
    g.add_node("nephrology", specialists.nephrology)
    g.add_node("pharmacy", specialists.pharmacy)
    g.add_node("evidence_rag", evidence_rag)
    g.add_node("nurse_feedback", specialists.nurse_feedback)
    g.add_node("chief", chief)
    g.add_node("safety", safety)
    g.add_node("human_review", human_review)
    g.add_node("notify", notify)

    g.add_edge(START, "intake")
    for name in SPECIALISTS:
        g.add_edge("intake", name)       # fan-out: 같은 super-step 에서 병렬 실행
    g.add_edge(SPECIALISTS, "chief")     # fan-in: 전부 끝나야 chief
    g.add_edge("chief", "safety")
    g.add_conditional_edges("safety", route_after_safety, ["human_review", END])
    g.add_edge("notify", END)
    return g.compile(checkpointer=checkpointer or MemorySaver())


if __name__ == "__main__":
    print(build_graph().get_graph().draw_mermaid())
