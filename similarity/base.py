"""유사환자 검색 인터페이스 (PLUG-IN 2: 유사환자 네트워크).

유사환자 팀 코드가 오면 similarity/team_adapter.py 의 find() 안에서 호출하고 .env 에 SIMILAR_BACKEND=team.
반환 형식만 지키면 된다: list[SimilarCase(case_id, similarity, key_features, outcome)]
"""
from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from config import settings
from data.schema import Patient, SimilarCase


class SimilarPatientFinder(Protocol):
    def find(self, patient: Patient, k: int = 5) -> list[SimilarCase]: ...


@lru_cache(maxsize=1)
def get_similar_finder() -> SimilarPatientFinder:
    if settings.SIMILAR_BACKEND == "team":
        from .team_adapter import TeamSimilarFinder

        return TeamSimilarFinder()
    from .mock_finder import MockSimilarFinder

    return MockSimilarFinder()
