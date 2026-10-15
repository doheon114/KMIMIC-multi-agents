"""데이터 구조 정의. 다른 팀(RAG, 유사환자)과 주고받는 형태도 여기서 고정한다."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Patient(BaseModel):
    """대시보드 왼쪽 'Patient Information' 패널과 1:1로 대응."""

    patient_id: str = "MANUAL"
    age: int = Field(72, ge=18, le=110)
    sex: Literal["Female", "Male"] = "Female"
    # Vital signs
    sbp: int = Field(102, description="수축기 혈압 mmHg")
    hr: int = Field(88, description="심박수 bpm")
    # Lab results
    creatinine: float = Field(1.8, description="mg/dL")
    bun: float = Field(35, description="mg/dL")
    sodium: float = Field(132, description="mmol/L")
    potassium: float = Field(4.7, description="mmol/L")
    baseline_creatinine: Optional[float] = Field(None, description="기저 Cr, 없으면 None")
    spot_urine_na: Optional[float] = Field(None, description="이뇨제 투여 2시간 뒤 spot urine Na mmol/L")
    # Medication & output
    furosemide_dose_mg: float = Field(40, description="IV furosemide 1회 용량")
    urine_output_6h_ml: Optional[float] = Field(250, description="투여 후 6시간 소변량, 기록 불완전하면 None")
    home_loop_diuretic_mg: Optional[float] = Field(None, description="입원 전 경구 furosemide 환산 용량, 없으면 None")
    medications: list[str] = Field(default_factory=list, description="병용약 (영문 일반명 소문자)")
    # Additional information (스크린샷의 체크박스)
    no_baseline_renal_info: bool = True
    no_prior_diuretic: bool = True
    urine_record_incomplete: bool = False
    # 연락처 (SMS용, 데모에서는 가짜 번호)
    attending_name: str = "담당 의료진"
    attending_phone: str = "010-1234-5678"
    scenario: str = ""  # mock 환자 시나리오 설명


class SimilarCase(BaseModel):
    """유사환자 팀이 돌려줄 형태. 대시보드 '유사 환자 (Top 5)' 표의 한 줄."""

    case_id: str
    similarity: float
    key_features: str
    outcome: str  # "반응 개선" | "용량 증량" | ...


class EvidenceDoc(BaseModel):
    """RAG 팀이 돌려줄 형태. 대시보드 '주요 근거' 카드 하나."""

    title: str
    source: str  # "Guideline" | "PubMed" | ...
    year: int
    snippet: str
    url: str = ""


class AgentFinding(BaseModel):
    """모든 전문 에이전트의 공통 출력."""

    agent: str
    status: Literal["done", "error"] = "done"
    bullets: list[str]
    flags: list[str] = Field(default_factory=list, description="Safety Agent가 읽는 위험 신호 코드")
    data: dict = Field(default_factory=dict, description="숫자 결과 (eGFR, 반응 등급 등)")
