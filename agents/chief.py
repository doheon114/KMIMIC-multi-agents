"""Chief Agent (Supervisor). 전문 에이전트 결과를 모아 판단 등급, 신뢰도, 핵심 요약을 만든다.

강의 2.8 / 3.7 의 supervisor 역할. 단, 판단 기준은 설명 가능한 규칙이고 LLM은 요약 문장만 쓴다.
"""
from __future__ import annotations

from datetime import datetime

from llm import narrate

CRITICAL = {"HYPOTENSION", "HYPERKALEMIA", "AKI", "HYPONATREMIA_MOD", "DIGOXIN_HYPOK", "RAAS_HYPERK", "METFORMIN_RENAL"}
CAUTION = {"RESPONSE_POOR", "RESPONSE_BORDERLINE", "NSAID", "NO_BASELINE_CR", "MISSING_DATA",
           "EGFR_LT30", "HYPOKALEMIA", "HYPONATREMIA_MILD", "TACHYCARDIA"}


def _all_flags(state) -> set[str]:
    return {f for v in state["findings"].values() for f in v["flags"]}


def chief(state):
    """Supervisor. 전문 에이전트 결과를 모아 판단 등급, 신뢰도, 핵심 요약을 만든다."""
    f, d = state["findings"], state["derived"]
    flags = _all_flags(state)
    grade = d["response"]["grade"]

    if flags & CRITICAL:
        status = "CRITICAL"
    elif flags & CAUTION or grade != "Good":
        status = "REVIEW RECOMMENDED"
    else:
        status = "ON TRACK"

    # 신뢰도: 자료 완결성 + 유사환자 결과 일치도 (설명 가능한 단순 규칙)
    conf = 0.9
    nurse = f["Nurse Feedback"]["data"]["requests"]
    conf -= 0.1 * len(nurse)
    ev = f["Evidence RAG"]["data"]
    agree = ev["improved"] / max(ev["n"], 1)
    if (grade == "Good") != (agree >= 0.5):
        conf -= 0.1
    if grade == "Unknown":
        conf -= 0.1
    conf = round(min(0.95, max(0.3, conf)), 2)
    conf_label = "High" if conf >= 0.75 else "Moderate" if conf >= 0.5 else "Low"

    facts = [b for name in ("Cardiology", "Nephrology", "Pharmacy") for b in f[name]["bullets"][:2]]
    facts += [f"부족한 정보: {', '.join(nurse)}" if nurse else "필수 정보 모두 있음",
              f"종합 판단 {status}, 신뢰도 {conf:.0%}"]
    pharm_issues = f["Pharmacy"]["data"]["interactions"]
    fallback = [f["Cardiology"]["bullets"][0], f["Nephrology"]["bullets"][0],
                pharm_issues[0] if pharm_issues else f["Pharmacy"]["bullets"][0]]
    fallback.append(f"부족한 정보 {len(nurse)}건으로 판단에 제한이 있습니다." if nurse
                    else "필수 정보가 모두 확보되었습니다.")
    if status == "CRITICAL":
        fallback.append("안전 기준에 해당하는 이상 소견이 있어 즉시 의사 확인이 필요합니다.")
    elif status == "REVIEW RECOMMENDED":
        fallback.append("가이드라인과 유사 환자 사례를 근거로 의사 검토를 권장합니다.")
    else:
        fallback.append("현재 치료를 유지하며 경과 관찰을 권장합니다.")
    summary = narrate("심부전 팀 총괄", facts, fallback, n=4)

    return {"final": {"status": status, "response_grade": grade, "confidence": conf,
                      "confidence_label": conf_label, "summary": summary,
                      "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M")},
            "log": [f"Chief: {status} (conf {conf:.0%})"]}
