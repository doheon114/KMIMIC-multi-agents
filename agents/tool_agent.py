"""(선택) 도구를 스스로 골라 쓰는 ReAct 에이전트. 강의 3.4, 3.7 의 create_react_agent.

.env 에 AGENT_MODE=react 이고 실제 LLM이 연결돼 있을 때만 동작한다. 아니면 None 을 돌려주고
노드는 규칙 기반 요약을 쓴다. 출력은 llm.guard 로 숫자 환각을 검사하고, 실패하면 버린다.
"심사위원: 이거 그냥 워크플로 아닌가요?" → "Nephrology는 도구를 스스로 호출하는 에이전트 모드도 있습니다."
"""
from __future__ import annotations

import os

from data.schema import Patient
from llm import get_llm
from llm.guard import is_grounded
from tools.clinical_tools import NEPHRO_TOOLS

PROMPT = ("당신은 신장내과 보조 AI입니다. 도구로 수치를 계산·판정한 뒤, 의사에게 보여줄 한국어 요약 "
          "3줄을 '- '로 시작해 작성하세요. 도구 결과와 입력에 없는 수치는 쓰지 마세요.")


def maybe_tool_agent(role: str, p: Patient, facts: list[str]) -> list[str] | None:
    llm = get_llm()
    if os.getenv("AGENT_MODE", "rules") != "react" or llm is None:
        return None
    try:
        from langgraph.prebuilt import create_react_agent

        agent = create_react_agent(llm, NEPHRO_TOOLS, prompt=PROMPT)
        q = (f"환자: {p.age}세 {p.sex}, Cr {p.creatinine}, 기저 Cr {p.baseline_creatinine}, "
             f"Na {p.sodium}, K {p.potassium}, BUN {p.bun}")
        out = agent.invoke({"messages": [("user", q)]})
        tool_text = [m.content for m in out["messages"] if m.type == "tool"]
        lines = [l.strip().lstrip("-•* ").strip() for l in out["messages"][-1].content.splitlines() if l.strip()][:3]
        return lines if lines and is_grounded(lines, facts + [q] + tool_text) else None
    except Exception:  # noqa: BLE001
        return None
