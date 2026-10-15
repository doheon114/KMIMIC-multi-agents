import csv
import io
import pytest

from config.settings import Settings
from data.schemas import PatientInput
from evaluation.batch_runner import run_batch
from evaluation.demo_cases import make_demo_cases
from evaluation.metrics import routing_metrics

def test_thirty_demo_patients_run_and_export():
    patients = make_demo_cases()
    assert len(patients) == 30
    seen = []
    result = run_batch(patients, Settings(), on_progress=lambda i, n, r: seen.append((i, n)))
    assert seen == [(i, 30) for i in range(1, 31)]
    assert all(row["execution_status"] == "COMPLETED" for row in result.records)
    assert all(row["mini_calls"] == 0 and row["chief_calls"] == 0 for row in result.records)
    assert all(row["total_tokens"] == 0 for row in result.records)
    assert all(row["overall_status"] == "INSUFFICIENT_DATA" for row in result.records[25:])
    parsed = list(csv.DictReader(io.StringIO(result.csv_bytes().decode("utf-8-sig"))))
    assert len(parsed) == 30
    assert parsed[0]["patient_id"] == "SYNTH-EVAL-001"

def test_batch_continues_after_failure():
    class BrokenPipeline:
        def __init__(self, settings):
            pass
        def run(self, patient, on_progress=None):
            raise RuntimeError("Do not expose patient's note")
    patients = [PatientInput(patient_id="A"), PatientInput(patient_id="B")]
    result = run_batch(patients, Settings(), pipeline_factory=BrokenPipeline)
    assert [r["error"] for r in result.records] == ["RuntimeError", "RuntimeError"]
    assert "Do not expose" not in result.csv_bytes().decode("utf-8-sig")

def test_batch_rejects_duplicate_and_oversized_inputs():
    with pytest.raises(ValueError):
        run_batch([PatientInput(patient_id="same")] * 2, Settings())
    with pytest.raises(ValueError):
        run_batch([PatientInput(patient_id=str(i)) for i in range(31)], Settings())

def test_metrics_are_not_invented_without_labels():
    rows = [{"patient_id":"a", "execution_status":"COMPLETED", "overall_status":"REVIEW"},
            {"patient_id":"b", "execution_status":"COMPLETED", "overall_status":"OK"}]
    assert routing_metrics(rows,{})["routing_accuracy"] is None
    metrics = routing_metrics(rows,{"a":"REVIEW","b":"REVIEW"})
    assert metrics["review_sensitivity"] == 0.5
    assert metrics["review_false_negative_rate"] == 0.5
