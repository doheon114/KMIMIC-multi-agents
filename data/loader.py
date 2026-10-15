"""Upload adapters: normalized column names -> one well-typed patient snapshot."""
import csv
import io
import json
from pathlib import Path
from typing import Any

from data.schemas import PatientInput

ALIASES = {
    "id": "patient_id", "subject_id": "patient_id", "patientid": "patient_id",
    "gender": "sex", "sex_at_birth": "sex", "sbp_mmhg": "sbp",
    "systolic_bp": "sbp", "hr": "heart_rate", "pulse": "heart_rate",
    "creat": "creatinine", "cr": "creatinine", "bun_mg_dl": "bun",
    "na": "sodium", "k": "potassium", "urine_6h": "urine_output_6h_ml",
    "urine_output": "urine_output_6h_ml", "furosemide_mg": "furosemide_dose_mg",
    "dose_mg": "furosemide_dose_mg", "baseline_cr": "baseline_creatinine",
}

def _normalize(record: dict[str, Any]) -> dict[str, Any]:
    normalized = {}
    for key, value in record.items():
        if key is None:
            continue
        field = str(key).strip().lower().replace(" ", "_").replace("-", "_")
        field = ALIASES.get(field, field)
        if isinstance(value, str):
            value = value.strip()
            if value.lower() in {"", "none", "null", "nan", "n/a", "na", "not available", "unknown"}:
                value = None
        if field == "sex" and isinstance(value, str):
            value = {"f":"Female", "female":"Female", "m":"Male", "male":"Male"}.get(value.lower(), "Unknown")
        if field == "sex" and value is None:
            value = "Unknown"
        normalized[field] = value
    return normalized

def parse_patients(content: bytes, filename: str) -> list[PatientInput]:
    if len(content) > 5 * 1024 * 1024:
        raise ValueError("Demo upload limit is 5 MB")
    decoded = content.decode("utf-8-sig")
    extension = Path(filename).suffix.lower()
    if extension == ".csv":
        records = list(csv.DictReader(io.StringIO(decoded)))
    elif extension == ".json":
        obj = json.loads(decoded)
        records = obj if isinstance(obj, list) else [obj]
    else:
        raise ValueError("Only .csv and .json are supported")
    if not records or not all(isinstance(row, dict) for row in records):
        raise ValueError("Expected one or more JSON objects / CSV rows")
    if len(records) > 500:
        raise ValueError("Demo supports up to 500 rows per upload")
    return [PatientInput.model_validate(_normalize(row)) for row in records]

def load_sample() -> PatientInput:
    path = Path(__file__).with_name("sample_patients.csv")
    return parse_patients(path.read_bytes(), path.name)[0]
