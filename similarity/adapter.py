"""Swap mock search for professor's Python module without touching agents/UI."""
from importlib import import_module
from typing import Any
from config.settings import Settings
from data.schemas import PatientInput, SimilarPatient
from similarity.mock_retriever import find_similar_patients as mock_search

def _normalize(result: Any) -> list[SimilarPatient]:
    if isinstance(result, dict):
        result = result.get("similar_patients", [])
    if not isinstance(result, list):
        raise ValueError("Similarity output must be a list or {'similar_patients': list}")
    normalized = []
    for item in result:
        if isinstance(item, SimilarPatient):
            normalized.append(item)
        elif isinstance(item, dict):
            normalized.append(SimilarPatient.model_validate(item))
        else:
            raise ValueError("Invalid similar-patient record")
    return normalized

class SimilarityAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def find(self, patient: PatientInput, top_k: int = 5) -> list[SimilarPatient]:
        if self.settings.similarity_provider == "mock":
            return mock_search(patient, top_k)
        if self.settings.similarity_provider != "professor":
            raise ValueError(f"Unsupported SIMILARITY_PROVIDER: {self.settings.similarity_provider}")
        fn = getattr(import_module(self.settings.similarity_module), self.settings.similarity_function)
        return _normalize(fn(patient.model_dump(mode="python"), top_k=top_k))[:top_k]
