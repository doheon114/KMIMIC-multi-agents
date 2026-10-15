"""Small, testable numeric tools; these are not treatment recommendations."""
from data.schemas import PatientInput

def urine_output_per_hour(patient: PatientInput) -> float | None:
    if patient.urine_output_6h_ml is None:
        return None
    return round(patient.urine_output_6h_ml / 6.0, 1)

def missing_key_fields(patient: PatientInput) -> list[str]:
    essential = ["sbp", "heart_rate", "creatinine", "sodium", "potassium", "furosemide_dose_mg", "urine_output_6h_ml"]
    missing = [field for field in essential if getattr(patient, field) is None]
    # Missing baseline/dose timing/weight/history should remain visible even if acute snapshot is complete.
    if patient.baseline_creatinine is None:
        missing.append("baseline_creatinine")
    if patient.weight_kg is None:
        missing.append("weight_kg")
    if not patient.medication_history:
        missing.append("medication_history")
    return missing

def clinical_features(patient: PatientInput) -> dict[str, float | None]:
    return {
        "sbp_mmhg": patient.sbp,
        "heart_rate_bpm": patient.heart_rate,
        "creatinine_mg_dl": patient.creatinine,
        "sodium_mmol_l": patient.sodium,
        "potassium_mmol_l": patient.potassium,
        "furosemide_mg": patient.furosemide_dose_mg,
        "urine_output_6h_ml": patient.urine_output_6h_ml,
        "urine_output_ml_hour": urine_output_per_hour(patient),
    }
