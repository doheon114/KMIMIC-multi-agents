"""(선택) 우리 쪽에서 직접 가이드라인 벡터DB를 만들 때 쓰는 스크립트. RAG 팀이 DB를 주면 필요 없다.

강의 꿀팁:
- RAG 3.5 / LangGraph 2.2: 표는 마크다운 표로 바꿔야 검색에 잡힌다. UnstructuredMarkdownLoader 는 표를 없애므로
  .md 를 .txt 로 바꿔 TextLoader 로 읽는다.
- RAG 3.2: 최초 1회만 from_documents 로 저장하고 이후엔 persist_directory 로 재사용 (임베딩 비용 절약).
- RAG 3.2.2: chunk_size 1500 / overlap 200 은 출발점. k 와 함께 튜닝 대상.

사용: python -m rag.ingest rag/knowledge   (폴더 안 .md/.txt 를 읽어 rag/chroma_db 에 저장)
필요 패키지: langchain-chroma, langchain-text-splitters, langchain-community, langchain-openai
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(folder: str = "rag/knowledge", persist: str = "rag/chroma_db"):
    from langchain_chroma import Chroma
    from langchain_community.document_loaders import TextLoader
    from langchain_openai import OpenAIEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    docs = []
    for path in Path(folder).glob("*"):
        if path.suffix not in (".md", ".txt"):
            continue
        for d in TextLoader(str(path), encoding="utf-8").load():   # .md 도 TextLoader 로 → 표 유지
            d.metadata.update({"title": path.stem, "source": "Guideline", "year": 0})
            docs.append(d)
    chunks = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200).split_documents(docs)
    Chroma.from_documents(chunks, OpenAIEmbeddings(model="text-embedding-3-large"),
                          collection_name="hf_guidelines", persist_directory=persist)
    print(f"{len(chunks)} chunks → {persist}")


if __name__ == "__main__":
    main(*sys.argv[1:])
