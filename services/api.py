"""HF-PathGuard API 서버 (PLUG-IN 4: 웹).

실행: uvicorn services.api:app --reload --port 8000     문서: http://localhost:8000/docs
어떤 웹 프론트(Streamlit, React, 디자이너가 만든 HTML)든 이 API만 부르면 된다.

  GET  /api/patients                 mock 또는 대회 데이터 환자 목록
  GET  /api/patients/{id}            환자 1명
  POST /api/analyze                  {"patient_id": "P-001"} 또는 {"patient": {...}} → 분석 결과
  POST /api/analyze/stream           같은 입력, Server-Sent Events 로 에이전트 진행 상황 실시간 전송
  POST /api/review/{thread_id}       {"action": "approve|edit|reject", "sms": "..."} 의사 승인
  GET  /api/messages                 발송된 알림 기록
  GET  /api/graph                    그래프 구조 (mermaid)
"""
from __future__ import annotations

import json
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import settings
from data.loaders import get_patient, load_patients
from data.schema import Patient
from services import runner
from services.notifier import read_log

app = FastAPI(title="HF-PathGuard API", version="0.2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class AnalyzeRequest(BaseModel):
    patient_id: Optional[str] = None
    patient: Optional[Patient] = None


class ReviewRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    sms: Optional[str] = None


def _resolve(req: AnalyzeRequest) -> Patient:
    if req.patient is not None:
        return req.patient
    if req.patient_id and (p := get_patient(req.patient_id)):
        return p
    raise HTTPException(404, f"환자를 찾을 수 없습니다: {req.patient_id}")


@app.get("/api/health")
def health():
    return {"ok": True, "llm": settings.LLM_PROVIDER, "data": settings.DATA_SOURCE,
            "rag": settings.RAG_BACKEND, "similar": settings.SIMILAR_BACKEND}


@app.get("/api/patients")
def patients():
    return [{"patient_id": p.patient_id, "age": p.age, "sex": p.sex, "scenario": p.scenario}
            for p in load_patients().values()]


@app.get("/api/patients/{patient_id}")
def patient(patient_id: str):
    if p := get_patient(patient_id):
        return p
    raise HTTPException(404, "not found")


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    return runner.analyze(_resolve(req))


@app.post("/api/analyze/stream")
def analyze_stream(req: AnalyzeRequest):
    p = _resolve(req)

    def events():
        for ev in runner.stream_analyze(p):
            yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/api/review/{thread_id}")
def review(thread_id: str, req: ReviewRequest):
    return runner.review(thread_id, req.action, req.sms)


@app.get("/api/messages")
def messages():
    return read_log()


@app.get("/api/graph")
def graph():
    return {"mermaid": runner.graph().get_graph().draw_mermaid()}
