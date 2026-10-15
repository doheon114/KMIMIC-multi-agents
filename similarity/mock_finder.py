"""mock 유사환자 검색: 가상 코호트 300명에서 표준화 거리로 Top-k. 유사환자 팀 결과로 교체 예정."""
from __future__ import annotations

import math

from data.mock_patients import generate_cohort
from data.schema import Patient, SimilarCase

_FEATS = [("age", 15), ("sbp", 20), ("creatinine", 0.6), ("sodium", 4), ("potassium", 0.6),
          ("furosemide_dose_mg", 40), ("urine_output_6h_ml", 400)]


def _describe(p: Patient) -> str:
    bits = []
    if p.age >= 75:
        bits.append("고령")
    if p.sbp < 100:
        bits.append("저혈압")
    if p.creatinine >= 1.5:
        bits.append("신기능 저하")
    if p.sodium < 135:
        bits.append("저나트륨")
    if p.potassium > 5.0:
        bits.append("고칼륨")
    return ", ".join(bits[:2]) or "유사한 연령/신장기능"


class MockSimilarFinder:
    """표준화한 유클리드 거리로 가상 코호트에서 Top-k. 유사환자 팀 결과로 교체 예정."""

    def __init__(self):
        self.cohort = generate_cohort()

    def find(self, patient: Patient, k: int = 5) -> list[SimilarCase]:
        def dist(q: Patient) -> float:
            return math.sqrt(sum(((getattr(patient, f) or 0) - (getattr(q, f) or 0)) ** 2 / s**2 for f, s in _FEATS))

        ranked = sorted(self.cohort, key=lambda c: dist(c["patient"]))[:k]
        return [SimilarCase(case_id=c["case_id"], similarity=round(1 / (1 + 0.35 * dist(c["patient"])), 2),
                            key_features=_describe(c["patient"]), outcome=c["outcome"]) for c in ranked]
