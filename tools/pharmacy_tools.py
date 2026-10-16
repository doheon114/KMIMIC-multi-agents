import json
import re
from langchain_core.tools import tool
from data.schemas import PatientInput

# DISCUSS!
DRUG_CLASSES = {
    "nsaid": r"nsaid|ibuprofen|naproxen|diclofenac|celecoxib|ketorolac|indomethacin",
    "loop_diuretic": r"furosemide|lasix|torsemide|bumetanide",
    "thiazide": r"hydrochlorothiazide|hctz|chlorthalidone|metolazone|indapamide",
    "k_sparing": r"spironolactone|eplerenone|amiloride|triamterene|finerenone",
    "raas": r"\w+pril\b|\w+sartan\b|sacubitril|entresto",
    "potassium_supplement": r"potassium chloride|\bkcl\b|k-dur",
    "digoxin": r"digoxin|lanoxin",
    "metformin": r"metformin",
}

def _classes(patient: PatientInput) -> set[str]:
    text = (patient.medication_history or "").lower()
    found = {name for name, pattern in DRUG_CLASSES.items() if re.search(pattern, text)}
    if patient.furosemide_dose_mg:
        found.add("loop_diuretic")
    return found
# re.search(): 정규표현식(Regular Expression)을 이용해 문자열에서 특정 패턴을 찾는 함수

# eGFR 계산
def egfr_ckd_epi_2021(patient: PatientInput) -> float | None:
    """CKD-EPI 2021 (race-free). Needs creatinine, age and a binary sex."""
    if patient.creatinine is None or not patient.creatinine or patient.age is None \
            or patient.sex not in {"Female", "Male"}:
        return None
    female = patient.sex == "Female"
    kappa, alpha = (0.7, -0.241) if female else (0.9, -0.302)
    ratio = patient.creatinine / kappa
    value = 142 * min(ratio, 1) ** alpha * max(ratio, 1) ** -1.200 * 0.9938 ** patient.age
    return round(value * (1.012 if female else 1), 1)


def check_drug_interactions(patient: PatientInput) -> dict:
    if not patient.medication_history:
        return {"tool": "drug_interactions", "flags": [], "status": "medication history missing; cannot check"}
    c = _classes(patient)
    flags = []
    if {"nsaid", "loop_diuretic"} <= c:
        flags.append("NSAID + loop diuretic: blunted diuretic response and AKI risk")
    if {"nsaid", "loop_diuretic"} <= c and c & {"raas", "k_sparing"}:
        flags.append("NSAID + diuretic + RAAS/K-sparing ('triple whammy'): AKI risk")
    if {"loop_diuretic", "thiazide"} <= c:
        flags.append("Loop + thiazide: risk of marked K/Na depletion")
    if "digoxin" in c and patient.potassium is not None and patient.potassium < 3.5:
        flags.append(f"Digoxin with low potassium (K={patient.potassium}): toxicity risk")
    return {"tool": "drug_interactions", "drug_classes": sorted(c), "flags": flags}


def check_renal_dosing(patient: PatientInput) -> dict:
    egfr = egfr_ckd_epi_2021(patient)
    c = _classes(patient)
    flags = []
    if egfr is not None and egfr < 30:
        flags.append(f"eGFR {egfr} < 30: renally cleared drugs need review; diuretic response may be reduced")
    if egfr is not None and egfr < 45 and c & {"metformin", "k_sparing", "digoxin", "nsaid"}:
        drugs = ", ".join(sorted(c & {"metformin", "k_sparing", "digoxin", "nsaid"}))
        flags.append(f"eGFR {egfr} < 45 with renally sensitive drug(s): {drugs}")
    if patient.baseline_creatinine and patient.creatinine is not None \
            and patient.creatinine - patient.baseline_creatinine >= 0.3:
        flags.append("Creatinine rise >= 0.3 mg/dL from baseline: re-check renally dosed drugs")
    return {"tool": "renal_dosing", "egfr_ckd_epi_2021": egfr, "creatinine": patient.creatinine,
            "baseline_creatinine": patient.baseline_creatinine, "flags": flags,
            **({} if egfr is not None else {"status": "eGFR not computable (needs creatinine, age, sex)"})}

# 칼륨·나트륨 수치와 약물 계열을 함께 확인하는 함수
def check_electrolytes(patient: PatientInput) -> dict:
    k, na = patient.potassium, patient.sodium
    c = _classes(patient)
    flags = []
    if k is not None and k >= 5.0 and c & {"k_sparing", "raas", "potassium_supplement"}:
        flags.append(f"K={k} on K-raising drug(s): hyperkalemia risk")
    if k is not None and k < 3.5 and "loop_diuretic" in c:
        flags.append(f"K={k} on loop diuretic: hypokalemia")
    if na is not None and na < 130 and c & {"loop_diuretic", "thiazide"}:
        flags.append(f"Na={na} on diuretic(s): hyponatremia")
    return {"tool": "electrolytes", "potassium": k, "sodium": na, "flags": flags}

# 일반 python 함수를 Langchain tool로 
def make_pharmacy_tools(patient: PatientInput) -> list:
  
    @tool("check_drug_interactions")
    def check_drug_interactions_tool() -> str:
        """Check the patient's medication list for risky combinations (NSAID+diuretic, triple whammy, loop+thiazide, digoxin with low K)."""
        return json.dumps(check_drug_interactions(patient), ensure_ascii=False)

    @tool("check_renal_dosing")
    def check_renal_dosing_tool() -> str:
        """Compute eGFR (CKD-EPI 2021) and flag renally sensitive drugs or a creatinine rise."""
        return json.dumps(check_renal_dosing(patient), ensure_ascii=False)

    @tool("check_electrolytes")
    def check_electrolytes_tool() -> str:
        """Check potassium and sodium against the patient's diuretics and K-raising drugs."""
        return json.dumps(check_electrolytes(patient), ensure_ascii=False)

    return [check_drug_interactions_tool, check_renal_dosing_tool, check_electrolytes_tool]
