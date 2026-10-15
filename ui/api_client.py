"""웹 화면이 서버를 부르는 클라이언트.

API_URL 의 서버가 살아 있으면 HTTP 로, 죽어 있으면 같은 코드를 프로세스 안에서 직접 실행한다.
→ 시연 중 서버가 꺼져도 화면은 계속 동작한다.
"""
from __future__ import annotations

import json
import os
from typing import Iterator

import httpx

from data.schema import Patient

API_URL = os.getenv("API_URL", "http://localhost:8000")


class ApiClient:
    def __init__(self, base: str = API_URL):
        self.base = base.rstrip("/")
        try:
            self.remote = httpx.get(f"{self.base}/api/health", timeout=1.5).status_code == 200
        except httpx.HTTPError:
            self.remote = False

    @property
    def mode(self) -> str:
        return f"server {self.base}" if self.remote else "local (서버 없이 직접 실행)"

    def patients(self) -> list[dict]:
        if self.remote:
            return httpx.get(f"{self.base}/api/patients").json()
        from services.api import patients

        return patients()

    def patient(self, pid: str) -> Patient:
        if self.remote:
            return Patient(**httpx.get(f"{self.base}/api/patients/{pid}").json())
        from data.loaders import get_patient

        return get_patient(pid)

    def stream_analyze(self, patient: Patient) -> Iterator[dict]:
        if not self.remote:
            from services import runner

            yield from runner.stream_analyze(patient)
            return
        body = {"patient": patient.model_dump()}
        with httpx.stream("POST", f"{self.base}/api/analyze/stream", json=body, timeout=120) as r:
            for line in r.iter_lines():
                if line.startswith("data: "):
                    yield json.loads(line[6:])

    def review(self, thread_id: str, action: str, sms: str | None) -> dict:
        if self.remote:
            return httpx.post(f"{self.base}/api/review/{thread_id}",
                              json={"action": action, "sms": sms}, timeout=60).json()
        from services import runner

        return runner.review(thread_id, action, sms)

    def messages(self) -> list[dict]:
        if self.remote:
            return httpx.get(f"{self.base}/api/messages").json()
        from services.notifier import read_log

        return read_log()
