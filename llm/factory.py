"""LLM 교체 지점. 새 모델을 쓰려면 PROVIDERS 에 함수 하나만 추가하고 .env 의 LLM_PROVIDER 를 바꾼다.

LLM_PROVIDER=mock 이면 None 을 돌려주고, 에이전트는 규칙 기반 문장을 쓴다 (API 키 없이 시연 가능).
"""
from __future__ import annotations

import os
from functools import lru_cache

from config import settings


def _openai():
    from langchain_openai import ChatOpenAI

    # OpenAI 호환 서버(vLLM, LM Studio, Azure 프록시 등)는 OPENAI_BASE_URL 만 바꾸면 된다
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                      base_url=os.getenv("OPENAI_BASE_URL") or None, temperature=0)


def _upstage():
    from langchain_upstage import ChatUpstage

    return ChatUpstage(model=os.getenv("UPSTAGE_MODEL", "solar-pro"), temperature=0)


def _ollama():
    from langchain_ollama import ChatOllama

    return ChatOllama(model=os.getenv("OLLAMA_MODEL", "gemma2"), temperature=0)


PROVIDERS = {
    "mock": lambda: None,
    "openai": _openai,
    "upstage": _upstage,
    "ollama": _ollama,
    # "anthropic": _anthropic,  ← 새 모델은 이렇게 추가
}


def provider() -> str:
    return settings.LLM_PROVIDER


@lru_cache(maxsize=1)
def get_llm():
    if settings.LLM_PROVIDER not in PROVIDERS:
        raise ValueError(f"알 수 없는 LLM_PROVIDER: {settings.LLM_PROVIDER} (가능: {list(PROVIDERS)})")
    return PROVIDERS[settings.LLM_PROVIDER]()
