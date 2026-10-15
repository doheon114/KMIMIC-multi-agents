"""전문 에이전트 노드들 (intake, Cardiology, Nephrology, Pharmacy, Nurse Feedback).

각 노드는 state를 받아 바뀐 부분만 dict로 돌려준다 (LangGraph 강의 2.1/2.2 패턴).

공통 구조: (1) clinical_rules 로 사실을 확정 → (2) llm.narrate 로 문장화 → (3) AgentFinding 반환.
"""
from __future__ import annotations

from data.schema import AgentFinding, Patient
from llm import narrate
from tools import clinical_rules as R

from .tool_agent import maybe_tool_agent


def _p(state) -> Patient:
    return Patient(**state["patient"])


def _out(f: AgentFinding) -> dict:
    return {"findings": {f.agent: f.model_dump()}}


# ------------------------------------------------------------------ intake
def intake(state):
    """입력 검증 + 공통 파생값 계산. 모든 전문 에이전트가 같은 숫자를 보게 한다."""
    p = _p(state)
    egfr = R.egfr_ckd_epi_2021(p.creatinine, p.age, p.sex)
    return {"derived": {"egfr": egfr, "response": R.diuretic_response(p), "flags": R.lab_flags(p, egfr)}}


# -------------------------------------------------------------- cardiology
def cardiology(state):
    p, d = _p(state), state["derived"]
    resp = d["response"]
    lo, hi = R.recommended_initial_dose(p)
    grade_ko = {"Good": "양호", "Borderline": "경계 수준", "Poor": "불충분", "Unknown": "판단 불가"}[resp["grade"]]
    facts = [f"이뇨제 반응 {grade_ko} ({', '.join(resp['reasons']) or '소변량 정보 없음'})",
             f"혈압 {p.sbp} mmHg, 심박수 {p.hr} bpm",
             f"현재 furosemide {p.furosemide_dose_mg:.0f} mg IV, 권장 초기 용량 {lo:.0f}~{hi:.0f} mg IV"]
    fallback = [{"Good": "이뇨제 반응이 양호합니다.", "Borderline": "이뇨제 반응이 경계 수준입니다.",
                 "Poor": "이뇨제 반응이 불충분할 가능성이 있습니다."}[resp["grade"]] if resp["grade"] != "Unknown" else "이뇨제 반응을 판단할 자료가 부족합니다."]
    if resp["rate"] is not None:
        fallback.append(f"6시간 소변량 {p.urine_output_6h_ml:.0f} mL ({resp['rate']:.0f} mL/h)")
    elif p.urine_output_6h_ml is not None:
        fallback.append(f"6시간 소변량 {p.urine_output_6h_ml:.0f} mL, 기록 불완전")
    if resp["grade"] in ("Poor", "Borderline"):
        fallback.append("ESC 알고리즘상 용량 2배 증량 검토 대상")
    if p.sbp < 90:
        fallback.append(f"저혈압(SBP {p.sbp}), 관류 저하 감별 필요")
    elif p.sbp < 105:
        fallback.append("혈압이 경계선상임")
    flags = [f for f in d["flags"] if f in ("HYPOTENSION", "TACHYCARDIA")]
    if resp["grade"] in ("Poor", "Borderline"):
        flags.append(f"RESPONSE_{resp['grade'].upper()}")
    return _out(AgentFinding(agent="Cardiology", bullets=narrate("심장내과", facts, fallback[:3]),
                             flags=flags, data={"grade": resp["grade"], "rate": resp["rate"],
                                                "dose_range": [lo, hi]}))


# -------------------------------------------------------------- nephrology
def nephrology(state):
    p, d = _p(state), state["derived"]
    egfr = d["egfr"]
    ratio = p.bun / p.creatinine
    facts = [f"Creatinine {p.creatinine} mg/dL, eGFR {egfr} (CKD-EPI 2021)",
             f"BUN {p.bun:.0f} mg/dL, BUN/Cr {ratio:.0f}",
             f"Na {p.sodium:.0f}, K {p.potassium}",
             f"기저 Cr {p.baseline_creatinine if p.baseline_creatinine else '정보 없음'}"]
    fallback = [f"Creatinine {p.creatinine} mg/dL (eGFR {egfr:.0f})"]
    if "AKI" in d["flags"]:
        fallback.append(f"기저 {p.baseline_creatinine} 대비 상승, AKI 기준 충족")
    elif p.baseline_creatinine is None:
        fallback.append("기저 Cr 없음, AKI 여부 판단 불가")
    fallback.append(f"BUN {p.bun:.0f} mg/dL, BUN/Cr {ratio:.0f}" + (" (상승)" if ratio > 20 else ""))
    if p.sodium < 135 or p.potassium > 5.0 or p.potassium < 3.5:
        fallback.append(f"전해질 이상 (Na {p.sodium:.0f}, K {p.potassium})")
    flags = [f for f in d["flags"] if f in ("AKI", "EGFR_LT30", "HYPERKALEMIA", "HYPOKALEMIA",
                                            "HYPONATREMIA_MOD", "HYPONATREMIA_MILD")]
    if p.baseline_creatinine is None:
        flags.append("NO_BASELINE_CR")
    bullets = maybe_tool_agent("신장내과", p, facts) or narrate("신장내과", facts, fallback[:3])
    return _out(AgentFinding(agent="Nephrology", bullets=bullets,
                             flags=flags, data={"egfr": egfr, "bun_cr": round(ratio, 1)}))


# ---------------------------------------------------------------- pharmacy
def pharmacy(state):
    p, d = _p(state), state["derived"]
    meds = {m.lower() for m in p.medications}
    issues, flags = [], []
    if meds & R.NSAIDS:
        issues.append(f"NSAID({', '.join(meds & R.NSAIDS)}) 병용: 이뇨 저항, 신기능 악화 위험")
        flags.append("NSAID")
    if (meds & (R.RAAS | R.MRA)) and p.potassium > 5.0:
        issues.append(f"K {p.potassium}에서 {', '.join(sorted(meds & (R.RAAS | R.MRA)))} 사용: 고칼륨 위험")
        flags.append("RAAS_HYPERK")
    if (meds & R.DIGOXIN) and p.potassium < 3.5:
        issues.append(f"digoxin + 저칼륨(K {p.potassium}): 독성 위험")
        flags.append("DIGOXIN_HYPOK")
    if (meds & R.METFORMIN) and d["egfr"] < 30:
        issues.append(f"eGFR {d['egfr']:.0f}에서 metformin: 금기 수준")
        flags.append("METFORMIN_RENAL")
    if (meds & R.SGLT2I) and d["egfr"] < 25:
        issues.append("eGFR 25 미만, SGLT2 억제제 신규 시작 기준 재확인")
    lo, hi = R.recommended_initial_dose(p)
    dose_note = (f"Furosemide {p.furosemide_dose_mg:.0f} mg: 권장 범위({lo:.0f}~{hi:.0f} mg) 내"
                 if lo <= p.furosemide_dose_mg <= hi
                 else f"Furosemide {p.furosemide_dose_mg:.0f} mg: 권장 범위({lo:.0f}~{hi:.0f} mg) 벗어남")
    renal_note = "신기능 저하로 loop 이뇨제 요구량 증가 가능" if d["egfr"] < 45 else "신기능상 용량 조정 불필요"
    facts = [dose_note, renal_note] + (issues or ["주요 약물 상호작용 없음"])
    fallback = [dose_note, renal_note] + (issues or ["병용약 상호작용 특이사항 없음"])
    return _out(AgentFinding(agent="Pharmacy", bullets=narrate("임상약학", facts, fallback[:3]),
                             flags=flags, data={"interactions": issues}))


# ---------------------------------------------------------- nurse feedback
def nurse_feedback(state):
    """부족한 데이터를 찾아 간호사에게 보낼 확인 요청 목록을 만든다."""
    p = _p(state)
    asks = []
    if p.urine_record_incomplete or p.urine_output_6h_ml is None:
        asks.append("6시간 소변량 기록 재확인 (I/O 차트)")
    if p.no_baseline_renal_info or p.baseline_creatinine is None:
        asks.append("최근 3개월 내 기저 Creatinine 확인")
    if p.spot_urine_na is None:
        asks.append("이뇨제 투여 2시간 뒤 spot urine Na 검사")
    if not p.no_prior_diuretic and p.home_loop_diuretic_mg is None:
        asks.append("입원 전 경구 이뇨제 용량 확인")
    return _out(AgentFinding(agent="Nurse Feedback", bullets=asks or ["추가 요청 없음"],
                             flags=["MISSING_DATA"] if asks else [], data={"requests": asks}))
