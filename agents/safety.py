"""Deterministic and fail-closed validation (non-clinical demo safeguards)."""
from data.schemas import EvidenceResult, PatientInput, SafetyResult, SpecialistResult
from tools.clinical_tools import missing_key_fields

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
