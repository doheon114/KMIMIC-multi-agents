"""근거 검색 인터페이스 (PLUG-IN 3: RAG).

RAG 팀 코드가 오면 rag/team_adapter.py 의 search() 안에서 호출하고 .env 에 RAG_BACKEND=team.
반환 형식만 지키면 된다: list[EvidenceDoc(title, source, year, snippet, url)]
에이전트는 이 retriever 를 직접 부르지 않고 rag/pipeline.py 를 거친다 (질의 재작성, 관련성 검사, fallback).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from config import settings
from data.schema import EvidenceDoc


class EvidenceRetriever(Protocol):
    def search(self, query: str, k: int = 3) -> list[EvidenceDoc]: ...


@lru_cache(maxsize=1)
def get_retriever() -> EvidenceRetriever:
    if settings.RAG_BACKEND == "team":
        from .team_adapter import TeamRetriever

        return TeamRetriever()
    from .mock_retriever import MockEvidenceRetriever

    return MockEvidenceRetriever()
