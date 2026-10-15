"""30 fictional records to exercise workflow routing—not clinical ground truth."""
from data.loader import load_sample
from data.schemas import PatientInput

def make_demo_cases() -> list[PatientInput]:
    base = load_sample().model_dump()
    patients = []
    for i in range(30):
        record = dict(base)
        record["patient_id"] = f"SYNTH-EVAL-{i + 1:03d}"
        record["clinical_note"] = f"Fictional evaluation case {i + 1}. No clinical conclusion implied."
        record["baseline_creatinine"] = 1.2
        record["weight_kg"] = 70.0
        record["medication_history"] = "Fictional medication history entered"
        if i < 5:
            # 정상 수치 케이스: OK -> Chief 생략 경로를 보여주기 위함
            record.update(creatinine=1.1, sodium=138, urine_output_6h_ml=900)
            record["clinical_note"] = f"Fictional stable case {i + 1}"
        elif 10 <= i < 20:
            record["baseline_creatinine"] = None
            record["clinical_note"] = "Fictional case with unknown renal baseline"
        elif 20 <= i < 25:
            record["medication_history"] = None
            record["clinical_note"] = "Fictional case with incomplete medication record"
        elif i >= 25:
            for field in ("sbp", "creatinine", "urine_output_6h_ml"):
                record[field] = None
        patients.append(PatientInput.model_validate(record))
    return patients
