"""결정론적 임상 규칙. 숫자 판단은 전부 여기서 하고, LLM은 설명만 한다.

근거 (요약, 원문 확인 필요):
- 이뇨제 반응: Mullens W, et al. Eur J Heart Fail 2019 (HFA position paper)
  투여 2시간 spot urine Na < 50~70 mmol/L 또는 첫 6시간 소변량 < 100~150 mL/h 이면 반응 불충분.
- 초기 용량: ESC 2021 HF guideline. 이뇨제 처음이면 IV furosemide 20~40 mg,
  기존 복용자는 경구 1일 용량의 1~2배를 IV로. 반응 불충분하면 용량 2배.
- eGFR: CKD-EPI 2021 (race-free) 식.
- AKI: KDIGO, 기저 대비 Cr 0.3 mg/dL 이상 상승.

데모용 기준이며 실제 진료 판단을 대체하지 않는다.
"""
from __future__ import annotations

from data.schema import Patient


def egfr_ckd_epi_2021(cr: float, age: int, sex: str) -> float:
    female = sex == "Female"
    kappa = 0.7 if female else 0.9
    alpha = -0.241 if female else -0.302
    ratio = cr / kappa
    egfr = 142 * min(ratio, 1) ** alpha * max(ratio, 1) ** -1.200 * 0.9938**age
    if female:
        egfr *= 1.012
    return round(egfr, 1)


def urine_rate_ml_per_h(p: Patient) -> float | None:
    if p.urine_output_6h_ml is None or p.urine_record_incomplete:
        return None
    return p.urine_output_6h_ml / 6


def diuretic_response(p: Patient) -> dict:
    """반환: {'grade': Good|Borderline|Poor|Unknown, 'rate': mL/h, 'reasons': [...]}"""
    rate = urine_rate_ml_per_h(p)
    reasons: list[str] = []
    grade = "Unknown"
    if rate is not None:
        if rate >= 150:
            grade = "Good"
        elif rate >= 100:
            grade = "Borderline"
        else:
            grade = "Poor"
        reasons.append(f"6시간 소변량 {p.urine_output_6h_ml:.0f} mL ({rate:.0f} mL/h)")
    elif p.urine_output_6h_ml is not None:
        reasons.append(f"6시간 소변량 {p.urine_output_6h_ml:.0f} mL (기록 불완전)")
        grade = "Poor" if p.urine_output_6h_ml / 6 < 100 else "Unknown"
    if p.spot_urine_na is not None:
        reasons.append(f"2시간 spot urine Na {p.spot_urine_na:.0f} mmol/L")
        if p.spot_urine_na < 50:
            grade = "Poor"
        elif p.spot_urine_na < 70 and grade == "Good":
            grade = "Borderline"
    return {"grade": grade, "rate": rate, "reasons": reasons}


def recommended_initial_dose(p: Patient) -> tuple[float, float]:
    """ESC 2021: 이뇨제 처음이면 20~40 mg IV, 기존 복용자는 경구 용량의 1~2배."""
    if p.home_loop_diuretic_mg:
        return p.home_loop_diuretic_mg, p.home_loop_diuretic_mg * 2
    return 20, 40


def lab_flags(p: Patient, egfr: float) -> list[str]:
    flags = []
    if p.sbp < 90:
        flags.append("HYPOTENSION")
    if p.hr > 120:
        flags.append("TACHYCARDIA")
    if p.potassium > 5.5:
        flags.append("HYPERKALEMIA")
    elif p.potassium < 3.5:
        flags.append("HYPOKALEMIA")
    if p.sodium < 130:
        flags.append("HYPONATREMIA_MOD")
    elif p.sodium < 135:
        flags.append("HYPONATREMIA_MILD")
    if p.baseline_creatinine is not None and p.creatinine - p.baseline_creatinine >= 0.3:
        flags.append("AKI")
    if egfr < 30:
        flags.append("EGFR_LT30")
    return flags


# 상호작용 사전. RAG 강의 3.6의 '키워드 사전' 아이디어를 약물에 적용.
NSAIDS = {"ibuprofen", "naproxen", "celecoxib", "diclofenac", "aceclofenac", "loxoprofen"}
RAAS = {"lisinopril", "enalapril", "ramipril", "losartan", "valsartan", "candesartan", "sacubitril/valsartan"}
MRA = {"spironolactone", "eplerenone"}
SGLT2I = {"dapagliflozin", "empagliflozin"}
DIGOXIN = {"digoxin"}
METFORMIN = {"metformin"}
