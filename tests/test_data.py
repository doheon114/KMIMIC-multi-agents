import pytest
from pydantic import ValidationError
from data.loader import parse_patients, load_sample

def test_sample_loaded_with_missing_baseline():
    p = load_sample()
    assert p.patient_id == "SYNTH-HF001"
    assert p.baseline_creatinine is None
    assert p.urine_output_6h_ml == 250

def test_csv_aliases_and_missing():
    p = parse_patients(b"subject_id,HR,creat,na,sex\nA1,80,1.7,134,F\n", "test.csv")[0]
    assert p.patient_id == "A1" and p.heart_rate == 80 and p.sex == "Female"

def test_json_validation():
    with pytest.raises(ValidationError):
        parse_patients(b'{"patient_id":"A1", "age":999}', "case.json")
