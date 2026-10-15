"""환자 데이터 받는 곳 (PLUG-IN 1: 데이터).

지금은 mock 환자. 대회 데이터를 받으면:
  1) CSV/엑셀을 data/raw/ 에 두고
  2) config/column_map.py 의 왼쪽 컬럼명만 실제 이름으로 바꾸고
  3) .env 에 DATA_SOURCE=csv, DATA_PATH=data/raw/파일명.csv
그래프, 서버, 웹은 손대지 않는다. 모두 Patient 객체만 보기 때문이다.
"""
from __future__ import annotations

import csv
from functools import lru_cache

from config import settings
from config.column_map import COLUMN_MAP, TRANSFORMS

from .mock_patients import SCENARIOS
from .schema import Patient

_BOOL_DEFAULTS = ("no_baseline_renal_info", "no_prior_diuretic", "urine_record_incomplete")


def row_to_patient(row: dict) -> Patient:
    data: dict = {}
    for col, field in COLUMN_MAP.items():
        v = row.get(col)
        if v is None or str(v).strip() in ("", "NA", "nan", "None"):
            continue
        data[field] = TRANSFORMS[field](v) if field in TRANSFORMS else v
    data["patient_id"] = str(data.get("patient_id", "UNKNOWN"))
    # 체크박스 값은 데이터에서 자동 추론
    data.setdefault("no_baseline_renal_info", "baseline_creatinine" not in data)
    data.setdefault("no_prior_diuretic", "home_loop_diuretic_mg" not in data)
    data.setdefault("urine_record_incomplete", "urine_output_6h_ml" not in data)
    if "urine_output_6h_ml" not in data:
        data["urine_output_6h_ml"] = None
    return Patient(**data)


def _load_csv(path) -> dict[str, Patient]:
    with open(path, newline="", encoding="utf-8-sig") as fp:
        return {p.patient_id: p for p in map(row_to_patient, csv.DictReader(fp))}


@lru_cache(maxsize=1)
def load_patients() -> dict[str, Patient]:
    if settings.DATA_SOURCE == "csv":
        return _load_csv(settings.DATA_PATH)
    return dict(SCENARIOS)


def get_patient(patient_id: str) -> Patient | None:
    return load_patients().get(patient_id)
