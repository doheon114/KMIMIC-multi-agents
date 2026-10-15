"""Stable input and output contracts for agents, RAG, similarity and web."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class PatientInput(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    patient_id: str = Field(min_length=1)
    age: int | None = Field(default=None, ge=0, le=120)
    sex: Literal["Female", "Male", "Other", "Unknown"] = "Unknown"
    sbp: float | None = Field(default=None, gt=0, lt=350)
    heart_rate: float | None = Field(default=None, gt=0, lt=300)
    creatinine: float | None = Field(default=None, ge=0, lt=40)
    baseline_creatinine: float | None = Field(default=None, gt=0, lt=40)
    bun: float | None = Field(default=None, ge=0, lt=300)
    sodium: float | None = Field(default=None, ge=70, le=200)
    potassium: float | None = Field(default=None, ge=1, le=12)
    furosemide_dose_mg: float | None = Field(default=None, ge=0, le=1000)
    urine_output_6h_ml: float | None = Field(default=None, ge=0, le=20000)
    weight_kg: float | None = Field(default=None, gt=0, le=400)
    medication_history: str | None = None
    clinical_note: str | None = None

class SpecialistResult(BaseModel):
    agent: Literal["cardiology", "nephrology", "pharmacy"]
    assessment: str
    concern_level: Literal["low", "moderate", "high", "unknown"] = "unknown"
    confidence: Literal["low", "moderate", "high", "unknown"] = "unknown"
    needs_review: bool = True
    reason: str

class EvidenceResult(BaseModel):
    summary: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    passages: list[dict[str, Any]] = Field(default_factory=list)
    evidence_found: bool = False
    refused: bool = False
    error: str | None = None

class SimilarPatient(BaseModel):
    patient_id: str
    similarity_score: float | None = None
    key_features: list[str] = Field(default_factory=list)
    observed_outcome: str | None = None

class SafetyResult(BaseModel):
    overall_status: Literal["OK", "REVIEW", "INSUFFICIENT_DATA"]
    review_reasons: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    notification_draft: str = ""

class ModelInfo(BaseModel):
    provider: str
    model_name: str

class FinalReport(BaseModel):
    patient_id: str
    cardiology: SpecialistResult
    nephrology: SpecialistResult
    pharmacy: SpecialistResult
    evidence: EvidenceResult = Field(default_factory=EvidenceResult)
    similar_patients: list[SimilarPatient] = Field(default_factory=list)
    overall_status: Literal["OK", "REVIEW", "INSUFFICIENT_DATA"]
    review_reasons: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    final_summary: str
    notification_draft: str = ""
    model_info: ModelInfo
    execution_time_seconds: float | None = None
    is_demo: bool = True
