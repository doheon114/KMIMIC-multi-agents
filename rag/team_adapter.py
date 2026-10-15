"""★ 현장에서 여기만 채운다: RAG 팀 연결.

경우 A) RAG 팀이 벡터DB(Chroma 폴더 등)를 넘겨준다 → 아래 예시 그대로 (강의 3.2: 저장된 DB 재사용)
경우 B) RAG 팀이 함수/체인을 넘겨준다 → search() 안에서 그 함수를 부르고 EvidenceDoc 으로 변환
경우 C) RAG 팀이 서버(API)를 띄운다 → requests.post(...) 결과를 EvidenceDoc 으로 변환
다 채우면 .env 에 RAG_BACKEND=team, python -m tests.smoke_test 로 확인.
"""
from __future__ import annotations

from data.schema import EvidenceDoc


class TeamRetriever:
    def __init__(self):
        # TODO 1 (경우 A 예시): 임베딩 모델은 RAG 팀이 DB 만들 때 쓴 것과 반드시 같아야 한다 (강의 3.4 교훈)
        # from langchain_chroma import Chroma
        # from langchain_openai import OpenAIEmbeddings
        # self.vs = Chroma(collection_name="hf_guidelines", persist_directory="rag/chroma_db",
        #                  embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"))
        raise NotImplementedError("rag/team_adapter.py 의 TODO 를 채워주세요")

    def search(self, query: str, k: int = 3) -> list[EvidenceDoc]:
        # TODO 2: 검색 결과 → EvidenceDoc. metadata 키 이름은 RAG 팀과 맞출 것
        # docs = self.vs.similarity_search(query, k=k)
        # return [EvidenceDoc(title=d.metadata.get("title", "문헌"), source=d.metadata.get("source", "Guideline"),
        #                     year=int(d.metadata.get("year", 0)), snippet=d.page_content[:200],
        #                     url=d.metadata.get("url", "")) for d in docs]
        raise NotImplementedError
