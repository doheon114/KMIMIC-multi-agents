"""알림 발송. 지금은 파일에 기록만 한다 (시연용).

실제 문자 서비스(NHN Cloud, Twilio 등)를 쓰려면 send_sms 안에서 API를 호출하면 된다.
그래프(agents/safety.py)는 이 함수만 부르므로 다른 곳은 바꿀 필요가 없다.
"""
from __future__ import annotations

import json
from datetime import datetime

from config import settings


def send_sms(patient_id: str, to: str, level: str, text: str) -> dict:
    rec = {"sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "patient_id": patient_id,
           "to": to, "level": level, "text": text, "channel": "mock"}
    settings.MESSAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with settings.MESSAGE_LOG.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def read_log() -> list[dict]:
    if not settings.MESSAGE_LOG.exists():
        return []
    lines = settings.MESSAGE_LOG.read_text(encoding="utf-8").splitlines()
    return [json.loads(l) for l in lines if l.strip()][::-1]
