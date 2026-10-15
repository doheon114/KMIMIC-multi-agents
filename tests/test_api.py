"""서버 엔드포인트 확인: python -m tests.test_api"""
import json

from fastapi.testclient import TestClient

from services.api import app

c = TestClient(app)


def main():
    assert c.get("/api/health").json()["ok"]
    assert len(c.get("/api/patients").json()) >= 1
    out = c.post("/api/analyze", json={"patient_id": "P-001"}).json()
    assert out["pending"] and out["result"]["final"]["status"] == "REVIEW RECOMMENDED"
    done = c.post(f"/api/review/{out['thread_id']}", json={"action": "edit", "sms": "수정된 문구"}).json()
    assert done["result"]["notification"]["text"] == "수정된 문구"
    with c.stream("POST", "/api/analyze/stream", json={"patient_id": "P-003"}) as r:
        events = [json.loads(l[6:]) for l in r.iter_lines() if l.startswith("data: ")]
    nodes = [e["node"] for e in events if e["type"] == "node"]
    assert nodes[0] == "intake" and "chief" in nodes and events[-1]["type"] == "result"
    assert c.get("/api/messages").json()[0]["text"] == "수정된 문구"
    print("API OK:", " > ".join(nodes))


if __name__ == "__main__":
    main()
