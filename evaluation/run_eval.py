"""평가 스크립트 (RAG 강의 5.1, LangGraph 4.2 아이디어: 정답셋을 먼저 만들고 수치로 비교).

지금은 mock 시나리오 5명의 기대 등급으로 정확도를 잰다. 대회 데이터가 오면:
  1) evaluation/labels.csv 에 patient_id, expected_status, expected_response 를 의료진과 함께 채우고
  2) python -m evaluation.run_eval
README 로드맵 v0.5 의 'Single LLM vs Multi-Agent' 비교는 single_llm_baseline() 을 실제 LLM 호출로 채워서 한다.
"""
from __future__ import annotations

import csv
from pathlib import Path

from data.loaders import load_patients
from llm import get_llm
from services import runner

LABELS = Path(__file__).parent / "labels.csv"
DEFAULT = {"P-001": ("REVIEW RECOMMENDED", "Poor"), "P-002": ("ON TRACK", "Good"),
           "P-003": ("CRITICAL", "Poor"), "P-004": ("CRITICAL", "Poor"), "P-005": ("REVIEW RECOMMENDED", "Borderline")}


def load_labels() -> dict:
    if not LABELS.exists():
        return DEFAULT
    with LABELS.open(encoding="utf-8-sig") as fp:
        return {r["patient_id"]: (r["expected_status"], r["expected_response"]) for r in csv.DictReader(fp)}


def single_llm_baseline(patient) -> tuple[str, str] | None:
    """비교군: LLM 하나에 환자 정보를 통째로 주고 등급을 묻는다. LLM 이 없으면 None (건너뜀)."""
    llm = get_llm()
    if llm is None:
        return None
    q = (f"급성 심부전 환자 {patient.model_dump_json()}\n"
         "status 를 CRITICAL / REVIEW RECOMMENDED / ON TRACK 중 하나, 이뇨제 반응을 Good / Borderline / Poor / Unknown 중 "
         "하나로 'status|response' 형식으로만 답하세요.")
    try:
        s, r = llm.invoke(q).content.strip().split("|")
        return s.strip(), r.strip()
    except Exception:  # noqa: BLE001
        return None


def main():
    labels, patients = load_labels(), load_patients()
    rows, hit_s, hit_r, base_s, n_base = [], 0, 0, 0, 0
    for pid, (exp_s, exp_r) in labels.items():
        p = patients.get(pid)
        if p is None:
            continue
        f = runner.analyze(p)["result"]["final"]
        hit_s += f["status"] == exp_s
        hit_r += f["response_grade"] == exp_r
        b = single_llm_baseline(p)
        if b:
            n_base += 1
            base_s += b[0] == exp_s
        rows.append((pid, exp_s, f["status"], exp_r, f["response_grade"], b[0] if b else "-"))
    n = len(rows)
    print(f"{'ID':<7}{'기대 등급':<20}{'Multi-Agent':<20}{'기대 반응':<12}{'MA 반응':<12}Single LLM")
    for r in rows:
        print(f"{r[0]:<7}{r[1]:<20}{r[2]:<20}{r[3]:<12}{r[4]:<12}{r[5]}")
    print(f"\nMulti-Agent  등급 정확도 {hit_s}/{n}  반응 정확도 {hit_r}/{n}")
    print(f"Single LLM   등급 정확도 {base_s}/{n_base}" if n_base else "Single LLM   (LLM_PROVIDER=mock 이라 생략)")


if __name__ == "__main__":
    main()
