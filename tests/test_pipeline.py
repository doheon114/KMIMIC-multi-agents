from config.settings import Settings
from data.loader import load_sample
from data.schemas import FinalReport, PatientInput
from services.pipeline import Pipeline
from evaluation.baseline import run_baseline

def test_end_to_end_mock():
    pipeline = Pipeline(Settings())
    patient = load_sample()
    report = pipeline.run(patient)
    assert isinstance(report, FinalReport)
    assert report.patient_id == patient.patient_id
    assert report.overall_status == "REVIEW"
    assert "baseline_creatinine" in report.missing_fields
    assert len(report.similar_patients) == 5
    assert report.evidence.evidence_found is False
    assert report.model_info.provider == "mock"
    assert "NOT SENT" in report.notification_draft or "No message has been sent" in report.notification_draft
    assert run_baseline(patient, pipeline.llm)["answer"]

def test_progress_events_match_graph_nodes():
    events = []
    pipeline = Pipeline(Settings())
    report = pipeline.run(load_sample(), on_progress=lambda node, state: events.append((node, state)))
    assert report.patient_id == "SYNTH-HF001"
    assert {node for node, state in events} == {
        "cardiology", "nephrology", "pharmacy", "evidence",
        "similarity", "safety", "final",
    }
    assert all(state == "completed" for _, state in events)
    assert events[-2:] == [("safety", "completed"), ("final", "completed")]

def test_incomplete_patient_abstention():
    report = Pipeline(Settings()).run(PatientInput(patient_id="SYNTH-EMPTY"))
    assert report.overall_status == "INSUFFICIENT_DATA"
    assert not report.similar_patients

def test_remote_inference_requires_explicit_permission():
    import pytest
    with pytest.raises(PermissionError):
        Pipeline(Settings(llm_provider="openai_compatible", llm_base_url="https://example.test/v1", llm_model="test"))
