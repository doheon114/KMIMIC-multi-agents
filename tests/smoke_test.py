"""API 키 없이 전체 흐름 확인: python -m tests.smoke_test
현장에서 데이터/유사환자/RAG 를 끼운 뒤에도 이것부터 돌린다."""
from __future__ import annotations

from data.loaders import load_patients
from data.mock_patients import generate_patient
from services import runner

EXPECTED = {"P-001": "REVIEW RECOMMENDED", "P-002": "ON TRACK", "P-003": "CRITICAL",
            "P-004": "CRITICAL", "P-005": "REVIEW RECOMMENDED"}


def main():
    for pid, p in load_patients().items():
        out = runner.analyze(p)
        if out["pending"]:
            out = runner.review(out["thread_id"], "approve")
        v = out["result"]
        f = v["final"]
        mark = "" if EXPECTED.get(pid, f["status"]) == f["status"] else "  ← 기대값과 다름"
        print(f"{pid} {f['status']:<19} resp={f['response_grade']:<10} conf={f['confidence']:.0%} "
              f"safety={v['safety']['level']:<8} sms={'sent' if v.get('notification') else '-'} "
              f"similar={len(v['similar'])} evidence={len(v['evidence'])}{mark}")
    for seed in range(20):
        out = runner.analyze(generate_patient(seed))
        if out["pending"]:
            runner.review(out["thread_id"], "reject")
    print("random 20 patients OK")


if __name__ == "__main__":
    main()
