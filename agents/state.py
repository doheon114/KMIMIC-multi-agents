"""그래프 State. 병렬 노드가 동시에 쓰는 키는 reducer 가 필요하다 (없으면 InvalidUpdateError, 강의 2.7)."""
from __future__ import annotations

import operator
from typing import Annotated

from typing_extensions import TypedDict


def merge_dicts(a: dict, b: dict) -> dict:
    return {**(a or {}), **(b or {})}


class PGState(TypedDict, total=False):
    patient: dict
    derived: dict
    findings: Annotated[dict, merge_dicts]
    evidence: list
    similar: list
    final: dict
    safety: dict
    review: dict
    notification: dict
    log: Annotated[list, operator.add]
