"""Deterministic and fail-closed validation (non-clinical demo safeguards)."""
from data.schemas import EvidenceResult, PatientInput, SafetyResult, SpecialistResult
from tools.clinical_tools import missing_key_fields, urine_output_per_hour

def validate_safety(patient: PatientInput, specialists: list[SpecialistResult],
                    evidence: EvidenceResult, similarity_error: str = "") -> SafetyResult:
    missing = missing_key_fields(patient)
    reasons = [f"Missing or unknown clinical information: {', '.join(missing)}"] if missing else []
    if not patient.clinical_note:
        reasons.append("Clinical context is missing")
    # This flags uncertainty, not an asserted medical threshold.
    for result in specialists:
        if result.needs_review:
            reasons.append(f"{result.agent}: {result.assessment}")
    if evidence.refused or evidence.error:
        reasons.append("Evidence retrieval refused or failed")
    if similarity_error:
        reasons.append("Similar-patient retrieval unavailable")
    RULES = [
        ("potassium", lambda v: v >= 5.5 or v < 3.0, "Potassium out of safe range"),
        ("sodium",    lambda v: v < 130,             "Hyponatremia"),
        ("sbp",       lambda v: v < 90,              "Hypotension (SBP < 90)"),
    ]
    for field, bad, label in RULES:
        v = getattr(patient, field)
        if v is not None and bad(v):
            reasons.append(f"RULE: {label} ({field}={v})")
    per_hour = urine_output_per_hour(patient)
    if per_hour is not None and per_hour < 100:
        reasons.append(f"RULE: Poor diuretic response ({per_hour} mL/h < 100)")
    if patient.baseline_creatinine and patient.creatinine is not None \
            and patient.creatinine - patient.baseline_creatinine >= 0.3:
        reasons.append("RULE: Creatinine rise >= 0.3 mg/dL (KDIGO AKI)")
    essential = {"sbp", "heart_rate", "creatinine", "sodium", "potassium", "furosemide_dose_mg", "urine_output_6h_ml"}
    if len(essential.intersection(missing)) >= 3:
        status = "INSUFFICIENT_DATA"
    elif reasons:
        status = "REVIEW"
    else:
        status = "OK"
    draft = (f"[HF-PathGuard DEMO] Patient {patient.patient_id}: {status}. "
             "Please review incomplete data and the specialist notes. No message has been sent.")
    return SafetyResult(overall_status=status, review_reasons=reasons, missing_fields=missing,
                        notification_draft=draft)
