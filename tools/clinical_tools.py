"""임상 규칙을 LangChain 도구(@tool)로 감싼 것. 강의 3.2~3.4, 3.8.

3.8 꿀팁: 도구 이름(함수명), docstring, 인자 이름이 곧 LLM에게 주는 설명서다.
LLM이 인자를 직접 채워 호출하므로 이름은 의미가 분명하게, 단위는 docstring에 적는다.
AGENT_MODE=react 일 때 agents/tool_agent.py 가 이 도구들을 쓰는 ReAct 에이전트를 만든다.
"""
from __future__ import annotations

from langchain_core.tools import tool

from . import clinical_rules as R


@tool
def calc_egfr(creatinine_mg_dl: float, age: int, sex: str) -> float:
    """CKD-EPI 2021 식으로 eGFR(mL/min/1.73m2)를 계산한다. sex 는 'Female' 또는 'Male'."""
    return R.egfr_ckd_epi_2021(creatinine_mg_dl, age, sex)


@tool
def check_aki(creatinine_mg_dl: float, baseline_creatinine_mg_dl: float) -> str:
    """KDIGO 기준으로 기저 Cr 대비 0.3 mg/dL 이상 상승했는지 판단한다. 기저값을 모르면 이 도구를 쓰지 않는다."""
    delta = creatinine_mg_dl - baseline_creatinine_mg_dl
    return f"Cr {delta:+.1f} mg/dL 변화, AKI {'해당' if delta >= 0.3 else '비해당'}"


@tool
def check_electrolytes(sodium_mmol_l: float, potassium_mmol_l: float) -> str:
    """나트륨, 칼륨 수치의 이상 여부를 판정한다."""
    out = []
    out.append("저나트륨(중등도 이상)" if sodium_mmol_l < 130 else "저나트륨(경도)" if sodium_mmol_l < 135 else "Na 정상")
    out.append("고칼륨" if potassium_mmol_l > 5.5 else "저칼륨" if potassium_mmol_l < 3.5 else "K 정상")
    return ", ".join(out)


NEPHRO_TOOLS = [calc_egfr, check_aki, check_electrolytes]
