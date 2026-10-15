"""HF-PathGuard interactive prototype. Run with: uv run streamlit run app.py"""
from pathlib import Path
import base64
from html import escape
import re
import pandas as pd
import streamlit as st
from pydantic import ValidationError

from config.settings import Settings
from data.loader import load_sample, parse_patients
from data.schemas import PatientInput, FinalReport
from evaluation.baseline import run_baseline
from evaluation.batch_runner import run_batch
from evaluation.demo_cases import make_demo_cases
from services.pipeline import Pipeline
from ui.styles import STYLE

st.set_page_config(page_title="HF-PathGuard", page_icon="🫀", layout="wide", initial_sidebar_state="expanded")
st.markdown(STYLE, unsafe_allow_html=True)

AGENT_LABELS = {
    "cardiology": "Cardiology", "nephrology": "Nephrology",
    "pharmacy": "Pharmacy", "evidence": "Evidence RAG",
    "similarity": "Similar Patients", "safety": "Safety", "final": "Chief",
}
BRANCHES = ("cardiology", "nephrology", "pharmacy", "evidence", "similarity")

@st.cache_data(show_spinner=False)
def robot_background() -> str:
    image_path = Path(__file__).parent / "ui" / "assets" / "dashboard_reference.png"
    return base64.b64encode(image_path.read_bytes()).decode("ascii")

def workflow_html(states: dict[str, str]) -> str:
    # This is a fixed reference illustration; only the overlaid status cards change.
    locations = {
        "cardiology": (17, 21), "nephrology": (17, 62),
        "pharmacy": (74, 9), "evidence": (74, 35),
        "similarity": (45, 79), "safety": (75, 67), "final": (42, 48),
    }
    cards = []
    for name, (x, y) in locations.items():
        state = states.get(name, "waiting")
        progress = 100 if state == "completed" else 0
        word = {"waiting": "Waiting", "running": "Analyzing…",
                "completed": "Completed", "failed": "Failed", "skipped": "Skipped"}.get(state, "Waiting")
        cards.append(
            f'<div class="hf-agent-status hf-{name} hf-{state}" '
            f'style="left:{x}%;top:{y}%">'
            f'<div class="hf-agent-line"><span>{escape(AGENT_LABELS[name])}</span>'
            f'<strong>{progress}%</strong></div>'
            f'<div class="hf-progress-track"><div class="hf-progress-fill" '
            f'style="width:{progress}%"></div></div>'
            f'<small>{word}</small></div>'
        )
    done = sum(states.get(name) == "completed" for name in AGENT_LABELS)
    return (
        '<section class="hf-workflow"><div class="hf-workflow-title">'
        '<b>✦ AI Agent 가동 중</b><span>로봇은 고정 · 상태바는 실제 실행에 연동</span></div>'
        '<div class="hf-workflow-stage" style="background-image:url(data:image/png;base64,'
        + robot_background() + ')">' + ''.join(cards) + '</div>'
        f'<div class="hf-workflow-foot">완료된 작업 <b>{done}/7</b>'
        '<span>실행 단계 기반 · 작업 중 시간 백분율은 추정하지 않음</span></div></section>'
    )

st.markdown("""<div class='hf-hero'><h1>💙 HF-PathGuard</h1>
<p>Safety-aware Multi-Agent Clinical Decision Support · Acute Heart Failure · Synthetic Research Demo</p></div>""", unsafe_allow_html=True)

settings = Settings.from_env()
with st.sidebar:
    st.markdown("### 🫀 HF-PathGuard")
    st.caption("Clinical Team · Synthetic Demo")
    st.divider()
    st.write("🏠 Home")
    st.write("👤 Patient Analysis")
    st.write("📋 Patient List")
    st.write("📚 Evidence & Similarity")
    st.write("🛡️ Safety Review")
    st.divider()
    st.caption(f"Mini: {settings.mini_llm_provider} / {settings.mini_llm_model}")
    st.caption(f"Chief: {settings.llm_provider} / {settings.llm_model}")
    st.caption(f"RAG: {settings.rag_provider} · Similarity: {settings.similarity_provider}")
    st.warning("Not for clinical decisions · No real SMS")

left, center, right = st.columns([1.12, 2.6, 1.48], gap="medium")
with left:
    st.subheader("👤 Patient Information")
    source = st.radio("Input mode", ["Demo Patient", "Upload CSV / JSON", "Manual Input"], horizontal=False)
    patient: PatientInput | None = None
    if source == "Demo Patient":
        patient = load_sample()
        st.success("Synthetic patient loaded")
        st.caption(f"Case: {patient.patient_id}")
        sample_path = Path(__file__).parent / "data" / "sample_patients.csv"
        st.download_button("Download sample CSV", sample_path.read_bytes(), file_name="sample_patients.csv", mime="text/csv")
    elif source == "Upload CSV / JSON":
        uploaded = st.file_uploader("Patient dataset", type=["csv", "json"])
        if uploaded:
            try:
                patients = parse_patients(uploaded.getvalue(), uploaded.name)
                selected = st.selectbox("Patient ID", list(range(len(patients))), format_func=lambda i:patients[i].patient_id)
                patient = patients[selected]
            except (ValidationError, ValueError, UnicodeError) as exc:
                st.error(f"Could not validate input: {exc}")
    else:
        # Key names and units match PatientInput. Empty numeric values remain None.
        with st.form("patient_form"):
            pid = st.text_input("Patient ID", "SYNTH-MANUAL")
            age = st.number_input("Age", 0, 120, 72)
            sex = st.selectbox("Sex", ["Female", "Male", "Other", "Unknown"])
            sbp = st.number_input("SBP (mmHg)", 1.0, 349.0, 102.0)
            hr = st.number_input("HR (bpm)", 1.0, 299.0, 88.0)
            cr = st.number_input("Creatinine (mg/dL)", 0.0, 39.0, 1.8)
            bun = st.number_input("BUN (mg/dL)", 0.0, 299.0, 35.0)
            na = st.number_input("Sodium (mmol/L)", 70.0, 200.0, 132.0)
            k = st.number_input("Potassium (mmol/L)", 1.0, 12.0, 4.7)
            dose = st.number_input("Furosemide dose (mg)", 0.0, 1000.0, 40.0)
            urine = st.number_input("6-hour urine (mL)", 0.0, 20000.0, 250.0)
            cr0 = st.text_input("Baseline creatinine (blank if unknown)", "")
            weight = st.text_input("Weight kg (blank if unknown)", "")
            meds = st.text_input("Medication history (blank if unknown)", "")
            note = st.text_area("Clinical note (optional)", "Synthetic demo only")
            valid = st.form_submit_button("Update patient input")
        if valid:
            st.session_state.pop("manual_patient", None)
            try:
                patient = PatientInput(patient_id=pid, age=age, sex=sex, sbp=sbp, heart_rate=hr,
                    creatinine=cr, bun=bun, sodium=na, potassium=k,
                    furosemide_dose_mg=dose, urine_output_6h_ml=urine,
                    baseline_creatinine=float(cr0) if cr0.strip() else None,
                    weight_kg=float(weight) if weight.strip() else None,
                    medication_history=meds or None, clinical_note=note or None)
                st.session_state["manual_patient"] = patient
            except (ValidationError, ValueError) as exc:
                st.error(f"Invalid patient data: {exc}")
        patient = st.session_state.get("manual_patient", patient)
    if patient:
        st.markdown("##### Data preview")
        st.dataframe(pd.DataFrame([
            {"field": key, "value": "—" if value is None else str(value)}
            for key, value in patient.model_dump(mode="json").items()
        ]), hide_index=True, height=280)
    baseline_enabled = st.checkbox("Compare single LLM baseline (extra model call)", value=False)
    run_clicked = st.button("▶ Run HF-PathGuard Analysis", type="primary", width="stretch", disabled=patient is None)

patient_signature = patient.model_dump_json() if patient is not None else None
if st.session_state.get("report_patient_signature") != patient_signature:
    st.session_state.pop("report", None)
    st.session_state.pop("baseline", None)
    st.session_state["agent_states"] = {name: "waiting" for name in AGENT_LABELS}

with center:
    st.subheader("🤖 Multi-Agent System")
    workflow_slot = st.empty()

agent_states = st.session_state.get("agent_states", {name: "waiting" for name in AGENT_LABELS})
workflow_slot.markdown(workflow_html(agent_states), unsafe_allow_html=True)

if run_clicked and patient:
    agent_states = {name: "waiting" for name in AGENT_LABELS}
    # Precheck runs first; no specialist/model jobs start before its decision.
    st.session_state["agent_states"] = agent_states
    workflow_slot.markdown(workflow_html(agent_states), unsafe_allow_html=True)

    def update_agent(node: str, state: str) -> None:
        if node == "dispatch":
            for branch in BRANCHES:
                agent_states[branch] = "running"
        if node == "abstain":
            for name in BRANCHES + ("safety",):
                agent_states[name] = "skipped"
            agent_states["final"] = "completed"
        if node == "mini_safety":
            agent_states["safety"] = "completed"
        if node == "safety":
            agent_states["safety"] = "running"
        if node in {"chief", "simple"}:
            agent_states["final"] = "running"
        if node not in agent_states:
            workflow_slot.markdown(workflow_html(agent_states), unsafe_allow_html=True)
            return
        if node != "safety":
            agent_states[node] = state
        if all(agent_states[b] == "completed" for b in BRANCHES):
            if agent_states["safety"] == "waiting":
                agent_states["safety"] = "running"
        if agent_states["safety"] == "completed" and agent_states["final"] == "waiting":
            agent_states["final"] = "running" if agent_states["final"] != "completed" else "completed"
        workflow_slot.markdown(workflow_html(agent_states), unsafe_allow_html=True)

    try:
        pipeline = Pipeline(settings)
        report = pipeline.run(patient, on_progress=update_agent)
        st.session_state["report"] = report
        st.session_state["report_patient_signature"] = patient_signature
        st.session_state["agent_states"] = agent_states.copy()
    except Exception as exc:
        for node, state in agent_states.items():
            if state == "running":
                agent_states[node] = "failed"
        st.session_state.pop("report", None)
        st.session_state.pop("baseline", None)
        st.session_state.pop("report_patient_signature", None)
        st.session_state["agent_states"] = agent_states.copy()
        workflow_slot.markdown(workflow_html(agent_states), unsafe_allow_html=True)
        st.error(f"Analysis could not complete ({type(exc).__name__}). Please review configuration and logs.")
    else:
        try:
            st.session_state["baseline"] = (run_baseline(patient, pipeline.llm)
                if baseline_enabled and report.overall_status != "INSUFFICIENT_DATA" else None)
        except Exception as exc:
            st.session_state["baseline"] = None
            st.warning(f"Optional baseline comparison unavailable ({type(exc).__name__}).")

report: FinalReport | None = st.session_state.get("report")
with center:
    st.subheader("🔶 Final Analysis")
    if not report:
        st.info("Select a synthetic patient and click Run Analysis to see the complete result.")
    else:
        status_color = {"REVIEW":"red", "INSUFFICIENT_DATA":"orange", "OK":"green"}[report.overall_status]
        st.markdown(f"**Status:** :{status_color}[{report.overall_status}] · **{report.execution_time_seconds}s**")
        st.write(report.final_summary)
        st.markdown("##### Specialist assessments")
        for label, result in [("🫀 Cardiology",report.cardiology),("🩺 Nephrology",report.nephrology),("💊 Pharmacy",report.pharmacy)]:
            with st.expander(f"{label} · {result.concern_level} · review={result.needs_review}", expanded=True):
                st.write(result.assessment)
                st.caption(result.reason)
        baseline = st.session_state.get("baseline")
        if baseline:
            st.markdown("##### Single LLM vs Multi-Agent")
            st.caption("Same patient; comparison is illustrative, not a validated performance result.")
            st.dataframe(pd.DataFrame([
                {"system":"Single LLM", "runtime (s)":baseline["duration_seconds"], "output":baseline["answer"]},
                {"system":"Multi-Agent", "runtime (s)":report.execution_time_seconds, "output":report.final_summary},
            ]), hide_index=True)

with right:
    st.subheader("📚 Similar Patients & Evidence")
    if report:
        st.caption("Synthetic top 5; scores are NOT clinical probabilities")
        if report.similar_patients:
            st.dataframe(pd.DataFrame([p.model_dump() for p in report.similar_patients]), hide_index=True, width="stretch")
        else:
            st.info("No similar patients returned")
        st.markdown("##### Evidence RAG")
        st.write(report.evidence.summary or "No evidence summary")
        st.caption("Verified evidence: No (unless independently confirmed)")
        if report.evidence.citations:
            st.json(report.evidence.citations)
        if report.evidence.error:
            st.warning(report.evidence.error)
    else:
        st.info("Evidence & similarity results will appear here.")
    st.subheader("🛡️ Safety & Alerts")
    if report:
        for reason in report.review_reasons:
            st.warning(reason)
        if not report.review_reasons:
            st.success("No demo review flags")
        st.text_area("Clinician review draft · NOT SENT", report.notification_draft, height=105, disabled=True)
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", report.patient_id)[:64]
        st.download_button("Download report JSON", report.model_dump_json(indent=2),
                           file_name=f"hf-pathguard-{safe_id}.json", mime="application/json")
    else:
        st.info("Safety review will appear after analysis.")

st.caption("Research prototype · Fictional data only · No diagnosis, treatment advice, or automated alerts")

st.divider()
with st.expander("🧪 Batch Evaluation · Up to 30 Patients", expanded=False):
    st.caption("Sequential processing. Synthetic research data only. A failed case will not stop the batch.")
    batch_mode = st.radio("Batch source", ["30 Synthetic Demo Cases", "Upload CSV / JSON"],
                          key="batch_mode", horizontal=True)
    batch_patients = None
    if batch_mode == "30 Synthetic Demo Cases":
        batch_patients = make_demo_cases()
        st.success(f"Prepared {len(batch_patients)} fictional patients")
    else:
        batch_file = st.file_uploader("Batch dataset (1–30 patients)", type=["csv", "json"],
                                      key="batch_upload")
        if batch_file:
            try:
                batch_patients = parse_patients(batch_file.getvalue(), batch_file.name)
                if len(batch_patients) > 30:
                    st.error("Batch limit: 30 patients per run")
                    batch_patients = None
                else:
                    st.info(f"Ready: {len(batch_patients)} patients")
            except (ValidationError, ValueError, UnicodeError) as exc:
                st.error(f"Could not validate batch: {exc}")
    st.warning("Remote GLM settings may send patient data outside this computer. "
               "Use only authorized data and verify API limits first.")
    if st.button("▶ Run Sequential Batch Evaluation",
                 disabled=not batch_patients, key="run_batch"):
        bar = st.progress(0, text="Preparing evaluation")
        status_area = st.empty()
        def update_batch(current: int, total: int, row: dict) -> None:
            bar.progress(current / total, text=f"Evaluated {current}/{total}")
            status_area.caption(f"Last: {row['patient_id']} · {row['execution_status']}")
        try:
            result = run_batch(batch_patients, settings, on_progress=update_batch)
            st.session_state["batch_result"] = result
        except Exception as exc:
            st.error(f"Batch could not start ({type(exc).__name__})")
    batch_result = st.session_state.get("batch_result")
    if batch_result:
        st.dataframe(pd.DataFrame(batch_result.records), hide_index=True, width="stretch")
        complete = sum(r["execution_status"] == "COMPLETED" for r in batch_result.records)
        st.caption(f"Completed: {complete}/{len(batch_result.records)} · "
                   "Token cells are blank if API usage is not reported; mock calls are not billed.")
        st.download_button("⬇ Download Batch Evaluation CSV", batch_result.csv_bytes(),
                           file_name="hf-pathguard-batch-results.csv", mime="text/csv",
                           key="download_batch")
