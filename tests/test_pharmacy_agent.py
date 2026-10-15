import json
from langchain_core.messages import AIMessage
from config.settings import Settings
from data.schemas import PatientInput, SpecialistResult
from agents.pharmacy_agent import MAX_ROUNDS, run_pharmacy_agent
from llm.factory import LLMClient
from tools.pharmacy_tools import check_drug_interactions, check_electrolytes, check_renal_dosing, egfr_ckd_epi_2021

STABLE = dict(patient_id="SYNTH-PH", age=60, sex="Male", sbp=115, heart_rate=80, creatinine=1.0,
              baseline_creatinine=1.0, sodium=138, potassium=4.2, furosemide_dose_mg=40,
              urine_output_6h_ml=900, weight_kg=70, medication_history="Bisoprolol", clinical_note="Synthetic")

def patient(**changes):
    return PatientInput(**{**STABLE, **changes})

def call(*names):
    return AIMessage(content="", tool_calls=[{"name": n, "args": {}, "id": f"c{i}", "type": "tool_call"}
                                             for i, n in enumerate(names)])

CLEAR = json.dumps({"assessment": "No issue", "concern_level": "low", "confidence": "moderate",
                    "needs_review": False, "reason": "Model says fine."})

class FakeClient:
    """Stands in for a remote model: replays scripted turns and records whether tools were bound."""
    is_mock = False
    def __init__(self, turns):
        self.turns, self.bound = list(turns), []
    def chat(self, messages, tools=None):
        self.bound.append(tools is not None)
        return self.turns.pop(0)
    def specialist(self, kind, p):
        return SpecialistResult(agent=kind, assessment="Plain specialist", needs_review=True, reason="fallback")

def test_rule_tools():
    assert check_drug_interactions(patient(medication_history="ibuprofen, furosemide, lisinopril"))["flags"]
    assert check_electrolytes(patient(potassium=5.6, medication_history="spironolactone"))["flags"]
    assert check_renal_dosing(patient(creatinine=3.0, baseline_creatinine=1.2))["flags"]
    assert 85 < egfr_ckd_epi_2021(patient()) < 90  # CKD-EPI 2021, 60M, Cr 1.0 -> ~86
    for check in (check_drug_interactions, check_electrolytes, check_renal_dosing):
        assert check(patient())["flags"] == []

def test_mock_agent_calls_tools_and_keeps_schema():
    result, called = run_pharmacy_agent(LLMClient(Settings(), tier="mini"),
                                        patient(medication_history="naproxen", potassium=5.8))
    assert called == ["check_drug_interactions", "check_renal_dosing", "check_electrolytes"]
    assert result.agent == "pharmacy" and result.needs_review
    assert "NSAID + loop diuretic" in result.reason and "Tools used:" in result.reason

def test_model_cannot_clear_tool_flag():
    fake = FakeClient([call("check_electrolytes"), AIMessage(content=CLEAR)])
    result, called = run_pharmacy_agent(fake, patient(potassium=5.9, medication_history="eplerenone"))
    assert called == ["check_electrolytes"]
    assert result.needs_review and result.concern_level == "moderate"
    assert "hyperkalemia" in result.reason

def test_model_may_skip_tools_and_clear_when_nothing_flags():
    result, called = run_pharmacy_agent(FakeClient([AIMessage(content=CLEAR)]), patient())
    assert called == [] and not result.needs_review and "Tools used: none" in result.reason

def test_tool_loop_is_capped_then_forced_final():
    fake = FakeClient([call("check_renal_dosing")] * MAX_ROUNDS + [AIMessage(content=CLEAR)])
    result, called = run_pharmacy_agent(fake, patient())
    assert len(called) == MAX_ROUNDS
    assert fake.bound == [True] * MAX_ROUNDS + [False]
    assert result.agent == "pharmacy"

def test_unparseable_answer_falls_back_to_plain_specialist():
    fake = FakeClient([call("check_drug_interactions"), AIMessage(content="not json")])
    result, _ = run_pharmacy_agent(fake, patient(medication_history="ibuprofen"))
    assert result.assessment == "Plain specialist" and result.needs_review
    assert "NSAID + loop diuretic" in result.reason
