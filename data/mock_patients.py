"""mock 환자 생성기.

- SCENARIOS: 시연용으로 손으로 만든 5명. 각자 다른 경로(정상, 검토, 위급)를 타도록 설계.
- generate_patient(seed): 무작위 환자 1명 (스트레스 테스트용).
- generate_cohort(n): 유사환자 mock 검색용 가상 코호트 (치료 결과 포함).
모두 가상 데이터이며 실제 환자 정보가 아니다.
"""
from __future__ import annotations

import random

from .schema import Patient

SCENARIOS: dict[str, Patient] = {
    "P-001": Patient(
        patient_id="P-001",
        scenario="스크린샷 환자: 이뇨제 반응 불충분 + 정보 부족 → 의사 검토",
        age=72, sex="Female", sbp=102, hr=88,
        creatinine=1.8, bun=35, sodium=132, potassium=4.7,
        furosemide_dose_mg=40, urine_output_6h_ml=250,
        medications=["aspirin", "atorvastatin"],
        no_baseline_renal_info=True, no_prior_diuretic=True, urine_record_incomplete=True,
    ),
    "P-002": Patient(
        patient_id="P-002",
        scenario="좋은 반응: 경과 관찰 (알림 없음)",
        age=65, sex="Male", sbp=128, hr=82,
        creatinine=1.1, bun=20, sodium=139, potassium=4.2, baseline_creatinine=1.0,
        spot_urine_na=95, furosemide_dose_mg=40, urine_output_6h_ml=1200,
        medications=["sacubitril/valsartan", "bisoprolol", "dapagliflozin"],
        no_baseline_renal_info=False, no_prior_diuretic=True,
    ),
    "P-003": Patient(
        patient_id="P-003",
        scenario="AKI + 고칼륨혈증 (MRA, ARNI 복용) → 위급",
        age=78, sex="Male", sbp=110, hr=96,
        creatinine=2.6, bun=58, sodium=136, potassium=5.9, baseline_creatinine=1.5,
        spot_urine_na=40, furosemide_dose_mg=80, urine_output_6h_ml=420,
        home_loop_diuretic_mg=40,
        medications=["spironolactone", "sacubitril/valsartan", "metformin"],
        no_baseline_renal_info=False, no_prior_diuretic=False,
    ),
    "P-004": Patient(
        patient_id="P-004",
        scenario="저혈압 + 중등도 저나트륨혈증, 이뇨제 장기 복용 → 위급",
        age=81, sex="Female", sbp=84, hr=112,
        creatinine=1.6, bun=48, sodium=126, potassium=3.3, baseline_creatinine=1.4,
        furosemide_dose_mg=80, urine_output_6h_ml=500, home_loop_diuretic_mg=80,
        medications=["digoxin", "bisoprolol", "empagliflozin"],
        no_baseline_renal_info=False, no_prior_diuretic=False,
    ),
    "P-005": Patient(
        patient_id="P-005",
        scenario="경계 반응 + NSAID 병용 → 검토",
        age=69, sex="Female", sbp=118, hr=90,
        creatinine=1.3, bun=28, sodium=137, potassium=4.4, baseline_creatinine=1.2,
        spot_urine_na=62, furosemide_dose_mg=40, urine_output_6h_ml=700,
        medications=["ibuprofen", "losartan", "amlodipine"],
        no_baseline_renal_info=False, no_prior_diuretic=True,
    ),
}

DRUG_POOL = [
    "aspirin", "atorvastatin", "bisoprolol", "carvedilol", "sacubitril/valsartan", "losartan",
    "spironolactone", "dapagliflozin", "empagliflozin", "digoxin", "metformin", "ibuprofen", "amlodipine",
]


def generate_patient(seed: int | None = None) -> Patient:
    r = random.Random(seed)
    sex = r.choice(["Female", "Male"])
    cr = round(max(0.6, r.gauss(1.5, 0.5)), 1)
    has_base = r.random() < 0.6
    prior = r.random() < 0.5
    incomplete = r.random() < 0.2
    return Patient(
        patient_id=f"R-{seed if seed is not None else r.randint(1000, 9999)}",
        scenario="무작위 생성",
        age=r.randint(45, 92), sex=sex,
        sbp=min(200, max(70, int(r.gauss(115, 18)))), hr=min(160, max(45, int(r.gauss(90, 15)))),
        creatinine=cr, bun=round(max(8, r.gauss(30, 12))),
        sodium=round(r.gauss(136, 4)), potassium=round(r.gauss(4.4, 0.6), 1),
        baseline_creatinine=round(max(0.5, cr - abs(r.gauss(0.2, 0.3))), 1) if has_base else None,
        spot_urine_na=round(max(10, r.gauss(70, 30))) if r.random() < 0.5 else None,
        furosemide_dose_mg=r.choice([20, 40, 40, 80, 120]),
        urine_output_6h_ml=round(max(50, r.gauss(750, 400)), -1),
        home_loop_diuretic_mg=r.choice([20, 40, 80]) if prior else None,
        medications=r.sample(DRUG_POOL, k=r.randint(1, 4)),
        no_baseline_renal_info=not has_base, no_prior_diuretic=not prior,
        urine_record_incomplete=incomplete,
    )


OUTCOMES = ["반응 개선", "용량 증량", "신기능 모니터링", "부분적 반응", "반응 불충분"]


def generate_cohort(n: int = 300, seed: int = 7) -> list[dict]:
    """유사환자 팀 데이터가 오기 전까지 쓰는 가상 코호트. 결과는 간단한 규칙 + 노이즈로 생성."""
    r = random.Random(seed)
    cohort = []
    for i in range(n):
        p = generate_patient(seed=10_000 + i)
        rate = (p.urine_output_6h_ml or 0) / 6
        if rate >= 150 and r.random() < 0.8:
            outcome = "반응 개선"
        elif p.creatinine >= 2.0 and r.random() < 0.6:
            outcome = "신기능 모니터링"
        elif rate < 100:
            outcome = r.choice(["용량 증량", "반응 불충분", "용량 증량"])
        else:
            outcome = r.choice(["부분적 반응", "반응 개선", "용량 증량"])
        cohort.append({"case_id": f"#{1000 + i * 7 % 9000}", "patient": p, "outcome": outcome})
    return cohort
