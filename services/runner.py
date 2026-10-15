"""그래프 실행 래퍼. 서버(services/api.py)와 웹(ui/)이 같은 함수를 쓴다.

thread_id = 분석 1회. checkpointer 가 thread_id 별로 상태를 저장해서, 의사 승인(resume)이
나중에 와도 멈춘 지점부터 이어간다 (강의 3.5, 3.6).
"""
from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Iterator

from langgraph.types import Command

from agents.graph import build_graph
from data.schema import Patient


@lru_cache(maxsize=1)
def graph():
    return build_graph()


def _snapshot(thread_id: str) -> dict:
    snap = graph().get_state({"configurable": {"thread_id": thread_id}})
    pending = None
    if snap.next and snap.tasks and snap.tasks[0].interrupts:
        pending = snap.tasks[0].interrupts[0].value
    return {"thread_id": thread_id, "result": snap.values, "pending": pending}


def stream_analyze(patient: Patient) -> Iterator[dict]:
    """노드가 끝날 때마다 {"type": "node"} 이벤트, 마지막에 {"type": "result"} 이벤트."""
    thread_id = str(uuid.uuid4())
    cfg = {"configurable": {"thread_id": thread_id}}
    for chunk in graph().stream({"patient": patient.model_dump()}, cfg, stream_mode="updates"):
        for node in chunk:
            if not node.startswith("__"):
                yield {"type": "node", "node": node}
    yield {"type": "result", **_snapshot(thread_id)}


def analyze(patient: Patient) -> dict:
    *_, last = stream_analyze(patient)
    return last


def review(thread_id: str, action: str, sms: str | None = None) -> dict:
    """action: approve | edit | reject"""
    cfg = {"configurable": {"thread_id": thread_id}}
    graph().invoke(Command(resume={"action": action, "sms": sms}), cfg)
    return _snapshot(thread_id)
