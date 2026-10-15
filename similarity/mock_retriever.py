"""Fictional nearest-neighbor *illustration*, not a clinical model."""
from math import sqrt
from data.schemas import PatientInput, SimilarPatient

# Synthetic reference patients; target variable scaling is demonstrative only.
REFERENCE = [
    ("SYNTH-1023", 70, 104, 1.7, 133),
    ("SYNTH-3912", 74, 98, 1.9, 130),
    ("SYNTH-2218", 67, 109, 2.1, 131),
    ("SYNTH-5581", 79, 100, 1.6, 135),
    ("SYNTH-7764", 63, 115, 1.4, 136),
    ("SYNTH-9011", 58, 122, 0.9, 140),
]

def find_similar_patients(patient: PatientInput, top_k: int = 5) -> list[SimilarPatient]:
    required = (patient.age, patient.sbp, patient.creatinine, patient.sodium)
    if any(value is None for value in required):
        return []
    scales = (20.0, 30.0, 1.5, 10.0)
    rows = []
    for row in REFERENCE:
        dist = sqrt(sum(((x-y)/scale)**2 for x,y,scale in zip(required, row[1:], scales)))
        # This is a *display similarity*, not a model probability/calibration.
        score = round(1.0 / (1.0 + dist), 3)
        rows.append(SimilarPatient(patient_id=row[0], similarity_score=score,
            key_features=["Synthetic feature-based example"], observed_outcome=None))
    return sorted(rows, key=lambda item:item.similarity_score or 0, reverse=True)[:top_k]
