"""HF-PathGuard Streamlit 대시보드. 화면 배치는 assets 의 시안 스크린샷과 같다.

  왼쪽: Patient Information (Manual Input / K-MIMIC Patient ID 탭)
  가운데: AI Agent 가동 현황 → 최종 분석 결과 → 전문의 Agent별 결과
  오른쪽: 유사 환자 / 근거 문헌 → 안전성 검토 → SMS 미리보기와 승인 (human-in-the-loop)

화면은 서버(services/api.py)만 부른다. 다른 웹 프론트로 바꿔도 서버는 그대로다.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import settings
from data.mock_patients import SCENARIOS
from data.schema import Patient
from ui.api_client import ApiClient

CSS = """
<style>
.block-container {padding-top: 1rem;}
.pg-header {background: linear-gradient(90deg,#0b1f4b,#1d3f8f); color:#fff; padding:14px 22px; border-radius:12px; margin-bottom:14px;}
.pg-header h1 {font-size:1.6rem; margin:0; color:#fff;} .pg-header p {margin:0; opacity:.8;}
.agent-wrap {background:#0d1b3d; border-radius:14px; padding:14px; margin-bottom:10px;}
.agent-wrap h4 {color:#fff; margin:0 0 4px 0;} .agent-wrap p {color:#aab6d6; margin:0 0 10px 0; font-size:.85rem;}
.agent {border-radius:12px; padding:10px 12px; margin-bottom:8px; color:#fff; min-height:78px;}
.agent b {font-size:.92rem;} .agent small {display:block; opacity:.85;}
.wait {background:#26304d;} .run {background:#1f4fd1; animation: pulse 1s infinite;} .done {background:#137a4b;}
@keyframes pulse {50% {opacity:.6;}}
.status {border-radius:12px; padding:14px; font-weight:700;}
.CRITICAL {background:#fde2e2; color:#b3121b; border:1px solid #f3a3a3;}
.REVIEW {background:#fff1e0; color:#b35a00; border:1px solid #f5c48a;}
.ONTRACK {background:#e2f6ea; color:#137a4b; border:1px solid #9bd8b3;}
.card {background:#f6f8fc; border:1px solid #e3e8f2; border-radius:12px; padding:12px; min-height:150px;}
.sms {background:#f3f0ff; border:1px solid #d8cffc; border-radius:10px; padding:10px; font-size:.9rem; white-space:pre-wrap;}
</style>
"""

AGENTS = [  # (그래프 노드, 화면 이름, 역할)
    ("chief", "Chief Agent", "종합 분석 및 의사결정"),
    ("cardiology", "Cardiology Agent", "심혈관 상태 분석"),
    ("nephrology", "Nephrology Agent", "신장기능 평가"),
    ("pharmacy", "Pharmacy Agent", "약물 상호작용 및 용량 검토"),
    ("evidence_rag", "Evidence RAG Agent", "근거 문헌, 유사 환자 검색"),
    ("safety", "Safety Agent", "안전성 검토"),
    ("nurse_feedback", "Nurse Feedback Agent", "추가 정보 요청 준비"),
]
SPECIALISTS = ["cardiology", "nephrology", "pharmacy", "evidence_rag", "nurse_feedback"]


def render_agents(box, status: dict):
    cells = []
    for node, name, role in AGENTS:
        s = status.get(node, "wait")
        label = {"wait": "대기", "run": "분석 중…", "done": "완료"}[s]
        cells.append(f'<div class="agent {s}"><b>{name}</b><small>{role}</small><small>● {label}</small></div>')
    grid = "".join(f'<div style="flex:1 1 23%">{c}</div>' for c in cells)
    box.markdown(f'<div class="agent-wrap"><h4>🤖 AI Agent 가동 현황</h4>'
                 f'<p>각 전문 에이전트가 협력하여 환자 데이터를 분석합니다.</p>'
                 f'<div style="display:flex;flex-wrap:wrap;gap:8px">{grid}</div></div>', unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="HF-PathGuard", page_icon="🫀", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    ss = st.session_state
    if "client" not in ss:
        ss.client = ApiClient()
    client: ApiClient = ss.client
    for k, v in {"thread_id": None, "result": None, "pending": None, "node_status": {}}.items():
        ss.setdefault(k, v)

    st.markdown('<div class="pg-header"><h1>🫀 HF-PathGuard</h1>'
                '<p>AI Clinical Decision Support for Acute Heart Failure · 가상 환자 데모</p></div>',
                unsafe_allow_html=True)
    page = st.sidebar.radio("메뉴", ["Patient Analysis", "Message Log", "Settings"])
    st.sidebar.caption("Smarter Decisions for Better Outcomes")

    if page == "Message Log":
        st.subheader("문자 알림 발송 기록")
        rows = client.messages()
        st.dataframe(pd.DataFrame(rows), width="stretch") if rows else st.info("아직 발송된 알림이 없습니다.")
        return
    if page == "Settings":
        st.subheader("연결 상태 (현장에서 끼운 모듈 확인용)")
        st.table(pd.DataFrame([
            ["서버", client.mode], ["LLM", settings.LLM_PROVIDER], ["환자 데이터", settings.DATA_SOURCE],
            ["유사환자", settings.SIMILAR_BACKEND], ["RAG", settings.RAG_BACKEND]], columns=["항목", "현재"]))
        st.caption("바꾸려면 .env 수정 후 서버와 웹을 다시 실행하세요. 자세한 방법은 docs/PLUGIN_GUIDE.md")
        return

    left, mid, right = st.columns([1.0, 2.1, 1.4], gap="medium")

    # ---------------------------------------------------------------- 입력
    def load(p: Patient):
        for k, v in p.model_dump().items():
            ss[f"in_{k}"] = v
        ss["meds_text"] = ", ".join(p.medications)

    if "in_age" not in ss:
        load(SCENARIOS["P-001"])

    with left:
        st.subheader("👤 Patient Information")
        tab_manual, tab_id = st.tabs(["Manual Input", "K-MIMIC (Patient ID)"])
        with tab_id:
            plist = client.patients()
            pid = st.selectbox("Patient ID", [p["patient_id"] for p in plist],
                               format_func=lambda i: next(f"{i} · {p['scenario'][:16]}" for p in plist
                                                          if p["patient_id"] == i))
            if st.button("불러오기", width="stretch"):
                load(client.patient(pid))
                st.rerun()
        with tab_manual:
            st.caption(ss.get("in_scenario", ""))
            with st.form("patient"):
                st.markdown("**Basic Information**")
                c1, c2 = st.columns(2)
                c1.number_input("Age", 18, 110, key="in_age")
                c2.selectbox("Sex", ["Female", "Male"], key="in_sex")
                st.markdown("**Vital Signs**")
                c1, c2 = st.columns(2)
                c1.number_input("SBP (mmHg)", 50, 250, key="in_sbp")
                c2.number_input("HR (bpm)", 30, 200, key="in_hr")
                st.markdown("**Lab Results**")
                c1, c2 = st.columns(2)
                c1.number_input("Creatinine (mg/dL)", 0.3, 15.0, step=0.1, key="in_creatinine")
                c2.number_input("BUN (mg/dL)", 2.0, 200.0, key="in_bun")
                c1.number_input("Sodium (mmol/L)", 110.0, 160.0, key="in_sodium")
                c2.number_input("Potassium (mmol/L)", 2.0, 8.0, step=0.1, key="in_potassium")
                st.markdown("**Medication & Output**")
                c1, c2 = st.columns(2)
                c1.number_input("Furosemide dose (mg)", 0.0, 500.0, key="in_furosemide_dose_mg")
                c2.number_input("Urine output (6h, mL)", 0.0, 5000.0, key="in_urine_output_6h_ml")
                with st.expander("Additional Information"):
                    st.checkbox("기저 신장기능 정보 없음", key="in_no_baseline_renal_info")
                    st.checkbox("이전 이뇨제 투여 이력 없음", key="in_no_prior_diuretic")
                    st.checkbox("6시간 소변량 기록 불완전", key="in_urine_record_incomplete")
                    st.text_input("병용약 (쉼표 구분)", key="meds_text")
                run = st.form_submit_button("▶ HF-PathGuard 분석 시작", type="primary", width="stretch")
        st.caption(f"연결: {client.mode}")

    def current_patient() -> Patient:
        data = {k: ss[f"in_{k}"] for k in Patient.model_fields if f"in_{k}" in ss}
        data["medications"] = [m.strip().lower() for m in ss.get("meds_text", "").split(",") if m.strip()]
        if data.get("no_baseline_renal_info"):
            data["baseline_creatinine"] = None
        return Patient(**data)

    # -------------------------------------------------------- 에이전트 현황
    with mid:
        agent_box = st.empty()
        render_agents(agent_box, ss.node_status)

    if run:
        status = {n: "run" for n in SPECIALISTS}
        render_agents(agent_box, status)
        for ev in client.stream_analyze(current_patient()):
            if ev["type"] == "node":
                status[ev["node"]] = "done"
                if all(status.get(n) == "done" for n in SPECIALISTS) and "chief" not in status:
                    status["chief"] = "run"
                if ev["node"] == "chief":
                    status["safety"] = "run"
                render_agents(agent_box, status)
            else:
                ss.thread_id, ss.result, ss.pending = ev["thread_id"], ev["result"], ev["pending"]
        ss.node_status = status

    res = ss.result
    if res is None:
        with mid:
            st.info("왼쪽에서 환자를 고르고 **분석 시작**을 누르세요.")
        return

    # ------------------------------------------------------------ 최종 결과
    final, findings = res["final"], res["findings"]
    with mid:
        st.markdown(f"#### 🔶 최종 분석 결과 <span style='float:right;font-size:.8rem;color:#888'>"
                    f"분석 완료: {final['finished_at']}</span>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1.4, 1, 1])
        cls = {"CRITICAL": "CRITICAL", "REVIEW RECOMMENDED": "REVIEW", "ON TRACK": "ONTRACK"}[final["status"]]
        msg = {"CRITICAL": "즉시 의사 확인이 필요합니다.", "REVIEW RECOMMENDED": "의사 검토가 필요한 사례입니다.",
               "ON TRACK": "현재 치료 유지, 경과 관찰"}[final["status"]]
        c1.markdown(f'<div class="status {cls}">⚠️ {final["status"]}<br><small>{msg}</small></div>',
                    unsafe_allow_html=True)
        grade_ko = {"Good": "반응 양호", "Borderline": "경계 반응", "Poor": "반응 불충분 가능성",
                    "Unknown": "판단 불가"}[final["response_grade"]]
        c2.metric("이뇨제 반응 추정", final["response_grade"])
        c2.caption(grade_ko)
        c3.metric("신뢰도", f"{final['confidence']:.0%}")
        c3.caption(final["confidence_label"])
        c3.progress(final["confidence"])

        st.markdown("**핵심 요약**")
        st.markdown("\n".join(f"- {s}" for s in final["summary"]))
        st.markdown("**전문의 Agent별 분석 결과**")
        for col, (name, icon) in zip(st.columns(3), [("Cardiology", "❤️"), ("Nephrology", "🫘"), ("Pharmacy", "💊")]):
            body = "".join(f"<li>{b}</li>" for b in findings[name]["bullets"])
            col.markdown(f'<div class="card"><b>{icon} {name}</b> <small style="color:#888">분석 완료</small>'
                         f'<ul style="padding-left:18px;margin-top:6px">{body}</ul></div>', unsafe_allow_html=True)
        with st.expander("Nurse Feedback Agent: 간호사 확인 요청"):
            st.markdown("\n".join(f"- {b}" for b in findings["Nurse Feedback"]["bullets"]))
        with st.expander("실행 로그"):
            st.write(res.get("log", []))
            st.caption(f"RAG 검색어: {findings['Evidence RAG']['data'].get('query')}")

    # ------------------------------------------------------- 근거 / 안전성
    with right:
        st.subheader("🧬 유사 환자 및 근거 정보")
        t1, t2 = st.tabs(["유사 환자 (Top 5)", "근거 문헌 / 가이드라인"])
        with t1:
            df = pd.DataFrame(res["similar"]).rename(columns={
                "case_id": "환자 ID", "similarity": "유사도", "key_features": "주요 특징", "outcome": "치료 결과"})
            st.dataframe(df, hide_index=True, width="stretch")
        with t2:
            for d in res["evidence"]:
                st.markdown(f"**[{d['title']}]({d['url']})** · `{d['source']} {d['year']}`  \n"
                            f"<small>{d['snippet']}</small>", unsafe_allow_html=True)

        st.subheader("🛡️ 안전성 검토 및 알림")
        sf = res["safety"]
        if sf["level"] == "NONE":
            st.success("특이 위험 신호 없음. 알림을 보내지 않습니다.")
            return
        (st.error if sf["level"] == "CRITICAL" else st.warning)("주의 사항이 발견되었습니다.")
        st.markdown("\n".join(f"- {a}" for a in sf["alerts"]))
        st.markdown("**📱 의료진 알림 (SMS)**")
        st.text(f"수신자: {sf['recipient']}")
        if ss.pending:
            text = st.text_area("알림 내용 미리보기", sf["sms_draft"], height=90)
            st.caption(f"{len(text.encode('euc-kr', errors='replace'))}/90 bytes")
            b1, b2 = st.columns(2)
            if b1.button("✈ 문자 알림 발송", type="primary", width="stretch"):
                action = "edit" if text != sf["sms_draft"] else "approve"
                out = client.review(ss.thread_id, action, text)
                ss.result, ss.pending = out["result"], None
                ss.node_status["safety"] = "done"
                st.rerun()
            if b2.button("발송 안 함", width="stretch"):
                out = client.review(ss.thread_id, "reject", None)
                ss.result, ss.pending = out["result"], None
                st.rerun()
        elif res.get("notification"):
            n = res["notification"]
            st.markdown(f'<div class="sms">{n["text"]}</div>', unsafe_allow_html=True)
            st.success(f"문자 알림이 발송되었습니다. ({n['sent_at']})")
        elif res.get("review"):
            st.info("의료진이 발송하지 않기로 했습니다.")
