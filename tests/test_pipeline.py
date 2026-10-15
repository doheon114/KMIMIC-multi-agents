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
        "similarity", "safety", "mini_safety", "precheck", "dispatch", "chief", "final",
    }
    assert all(state == "completed" for _, state in events)
    assert events[-3:] == [("mini_safety", "completed"), ("chief", "completed"), ("final", "completed")]

def test_incomplete_patient_abstention():
    pipeline = Pipeline(Settings())
    events = []
    report = pipeline.run(PatientInput(patient_id="SYNTH-EMPTY"),
                          on_progress=lambda node, state: events.append(node))
    assert report.overall_status == "INSUFFICIENT_DATA"
    assert not report.similar_patients
    assert events == ["precheck", "abstain"]
    assert report.model_info.provider == "none"

def test_mini_safety_cannot_clear_rule_review(monkeypatch):
    from llm.factory import SafetyAudit
    pipeline = Pipeline(Settings())
    monkeypatch.setattr(pipeline.mini_llm, "safety_audit",
                        lambda *args: SafetyAudit(needs_review=False, reason="No additional issues"))
    report = pipeline.run(load_sample())
    assert report.overall_status == "REVIEW"
    assert "baseline_creatinine" in report.missing_fields

def test_ok_route_skips_chief_and_mini_escalation_routes_chief(monkeypatch):
    from data.schemas import SpecialistResult
    from llm.factory import SafetyAudit
    patient = PatientInput(patient_id="SYNTH-OK", sbp=110, heart_rate=80,
        creatinine=1.2, baseline_creatinine=1.1, sodium=137, potassium=4,
        furosemide_dose_mg=40, urine_output_6h_ml=600, weight_kg=65,
        medication_history="Synthetic medications reviewed", clinical_note="Synthetic observation")
    pipeline = Pipeline(Settings())
    monkeypatch.setattr(pipeline.mini_llm, "specialist", lambda kind, p:
                        SpecialistResult(agent=kind, assessment="No additional flags",
                                         needs_review=False, reason="Test fixture"))
    monkeypatch.setattr(pipeline.mini_llm, "safety_audit",
                        lambda *args: SafetyAudit(needs_review=False, reason="No additional issues"))
    events = []
    report = pipeline.run(patient, on_progress=lambda node, state: events.append(node))
    assert report.overall_status == "OK"
    assert "simple" in events and "chief" not in events
    monkeypatch.setattr(pipeline.mini_llm, "safety_audit",
                        lambda *args: SafetyAudit(needs_review=True, reason="Additional uncertainty"))
    events.clear()
    report = pipeline.run(patient, on_progress=lambda node, state: events.append(node))
    assert report.overall_status == "REVIEW"
    assert "chief" in events and "simple" not in events
    assert any("Mini safety audit" in reason for reason in report.review_reasons)

def test_mini_remote_requires_permission():
    import pytest
    with pytest.raises(PermissionError):
        Pipeline(Settings(mini_llm_provider="openai_compatible",
                          mini_llm_base_url="https://example.test/v1", mini_llm_model="test"))

def test_remote_inference_requires_explicit_permission():
    import pytest
    with pytest.raises(PermissionError):
        Pipeline(Settings(llm_provider="openai_compatible", llm_base_url="https://example.test/v1", llm_model="test"))
