"""Safety Agent + human-in-the-loop + 알림 발송.

- 알림 여부는 규칙으로만 정한다 (LLM 판단 금지).
- human_review: 강의 3.6 의 interrupt + Command 패턴. 의사가 승인/수정/거절할 때까지 그래프가 멈춘다.
"""
from __future__ import annotations

from typing import Literal

from langgraph.graph import END
from langgraph.types import Command, interrupt

from data.schema import Patient
from services.notifier import send_sms

from .chief import _all_flags


def _sms_bytes(text: str) -> int:
    return len(text.encode("euc-kr", errors="replace"))


def safety(state):
    """위험 신호 정리 + 의료진 SMS 초안. 알림 여부는 규칙으로만 정한다 (LLM 판단 금지)."""
    p = Patient(**state["patient"])
    flags = _all_flags(state)
    status = state["final"]["status"]
    level = {"CRITICAL": "CRITICAL", "REVIEW RECOMMENDED": "CAUTION"}.get(status, "NONE")
    alerts = []
    for name in ("Cardiology", "Nephrology", "Pharmacy"):
        if state["findings"][name]["flags"]:
            alerts.append(state["findings"][name]["bullets"][0])
    alerts += state["findings"]["Nurse Feedback"]["data"]["requests"][:2]
    tag = "긴급" if level == "CRITICAL" else "검토"
    sms = f"[HF-PathGuard] {tag} 필요 사례입니다. Case ID: {p.patient_id}. 대시보드에서 확인해주세요."
    return {"safety": {"level": level, "alerts": alerts[:4], "flags": sorted(flags),
                       "sms_draft": sms, "sms_bytes": _sms_bytes(sms),
                       "recipient": f"{p.attending_name} ({p.attending_phone})"},
            "log": [f"Safety: {level}"]}


def route_after_safety(state) -> Literal["human_review", "__end__"]:
    return "human_review" if state["safety"]["level"] != "NONE" else END


def human_review(state) -> Command[Literal["notify", "__end__"]]:
    """의사가 SMS 발송을 승인/수정/거절할 때까지 멈춘다. 강의 3.6과 같은 interrupt 패턴."""
    decision = interrupt({
        "question": "아래 알림을 담당 의료진에게 보낼까요?",
        "level": state["safety"]["level"],
        "sms_draft": state["safety"]["sms_draft"],
        "recipient": state["safety"]["recipient"],
    })
    action = decision.get("action", "reject")
    if action == "reject":
        return Command(goto=END, update={"review": decision, "log": ["Human: 발송 거절"]})
    sms = decision.get("sms") or state["safety"]["sms_draft"]
    return Command(goto="notify", update={"review": {**decision, "sms": sms},
                                          "log": [f"Human: {action}"]})


def notify(state):
    """의사가 승인한 문구를 발송한다. 실제 발송 수단은 services/notifier.py 에서 교체."""
    rec = send_sms(patient_id=state["patient"]["patient_id"], to=state["safety"]["recipient"],
                   level=state["safety"]["level"], text=state["review"]["sms"])
    return {"notification": rec, "log": ["Notify: SMS 발송"]}
