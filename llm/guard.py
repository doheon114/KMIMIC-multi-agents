"""LLM 출력 검증 (Self-RAG 강의 2.4의 '답변이 근거에 기반했는가' 체크를 규칙으로 구현).

LLM이 쓴 문장에 '확정된 사실'에 없는 숫자가 나오면 환각으로 보고 버린다.
LLM 채점기(grader)보다 싸고, 임상 수치에는 이쪽이 더 확실하다.
"""
from __future__ import annotations

import re

_NUM = re.compile(r"\d+(?:\.\d+)?")


def numbers(text: str) -> set[str]:
    return {n.rstrip("0").rstrip(".") if "." in n else n for n in _NUM.findall(text)}


def is_grounded(lines: list[str], facts: list[str]) -> bool:
    allowed = numbers(" ".join(facts))
    used = numbers(" ".join(lines))
    return used <= allowed
