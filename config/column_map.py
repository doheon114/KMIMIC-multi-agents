"""데이터 시트 컬럼 → Patient 필드 매핑.

대회 데이터(K-MIMIC 등)를 받으면 왼쪽 값만 실제 컬럼명으로 바꾸면 된다.
매핑에 없는 Patient 필드는 기본값을 쓴다. 단위 변환이 필요하면 TRANSFORMS 에 함수를 넣는다.
"""

COLUMN_MAP = {
    # "데이터 시트 컬럼명": "Patient 필드명"
    "subject_id": "patient_id",
    "age": "age",
    "gender": "sex",
    "sbp": "sbp",
    "heart_rate": "hr",
    "creatinine": "creatinine",
    "bun": "bun",
    "sodium": "sodium",
    "potassium": "potassium",
    "baseline_creatinine": "baseline_creatinine",
    "spot_urine_na": "spot_urine_na",
    "furosemide_iv_mg": "furosemide_dose_mg",
    "urine_output_6h": "urine_output_6h_ml",
    "home_furosemide_mg": "home_loop_diuretic_mg",
    "medications": "medications",          # "a;b;c" 형태 문자열
    "urine_incomplete": "urine_record_incomplete",  # 1/0, Y/N
}

TRANSFORMS = {
    "sex": lambda v: "Female" if str(v).strip().upper() in ("F", "FEMALE", "여", "2") else "Male",
    "urine_record_incomplete": lambda v: str(v).strip().upper() in ("1", "Y", "YES", "TRUE"),
    "medications": lambda v: [m.strip().lower() for m in str(v).replace(",", ";").split(";") if m.strip()],
    # 예: Cr 이 umol/L 이면  "creatinine": lambda v: float(v) / 88.4,
}
