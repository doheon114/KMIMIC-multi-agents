"""Translate /api/ask's final SSE `done` payload to EvidenceResult."""
import json
from typing import Any, Iterable
import httpx

from config.settings import Settings
from data.schemas import EvidenceResult

def _items(value: Any) -> list[dict[str, Any]]:
    """Preserve fields from team API even if list members are strings."""
    if value is None:
        return []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        value = [value]
    return [item if isinstance(item, dict) else {"text": str(item)} for item in value]

def normalize_rag_payload(payload: dict[str, Any]) -> EvidenceResult:
    refused = bool(payload.get("refused", False))
    citations = _items(payload.get("cited"))
    passages = _items(payload.get("passages"))
    # Nonempty citations are not proof they support the claimed statement.
    return EvidenceResult(
        summary="" if refused else str(payload.get("answer") or ""),
        citations=citations, passages=passages,
        refused=refused, evidence_found=False,
        error=None if not refused else "RAG declined the question; evidence not verified",
    )

def last_done_payload(lines: Iterable[str]) -> dict[str, Any]:
    """Read SSE event/data frames; ignore incomplete partial progress events."""
    event_type = ""
    data_parts: list[str] = []
    last: dict[str, Any] | None = None

    def consume() -> None:
        nonlocal last, event_type, data_parts
        if data_parts:
            raw = "\n".join(data_parts)
            if raw != "[DONE]":
                try:
                    obj = json.loads(raw)
                    if isinstance(obj, dict) and (event_type == "done" or obj.get("event") == "done" or obj.get("type") == "done"):
                        last = obj.get("data") if isinstance(obj.get("data"), dict) else obj
                except json.JSONDecodeError:
                    pass
        event_type, data_parts = "", []

    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        line = line.rstrip("\r\n")
        if not line:
            consume()
        elif line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_parts.append(line[5:].strip())
    consume()
    if last is None:
        raise ValueError("No final SSE done event was received")
    return last

class EvidenceAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings

    def ask(self, query: str) -> EvidenceResult:
        if self.settings.rag_provider == "mock":
            return EvidenceResult(summary="Demo mode: no verified guideline or paper was retrieved.")
        if self.settings.rag_provider != "api":
            raise ValueError(f"Unsupported RAG_PROVIDER: {self.settings.rag_provider}")
        self.settings.require_remote_authorization()
        if not self.settings.rag_ask_url:
            raise ValueError("RAG_ASK_URL is required")
        headers = {"Accept":"text/event-stream, application/json"}
        if self.settings.rag_api_key:
            headers["Authorization"] = f"Bearer {self.settings.rag_api_key}"
        try:
            with httpx.Client(timeout=self.settings.rag_timeout_seconds) as client:
                with client.stream("POST", self.settings.rag_ask_url, json={"question":query}, headers=headers) as response:
                    response.raise_for_status()
                    if "text/event-stream" in response.headers.get("content-type", ""):
                        payload = last_done_payload(response.iter_lines())
                    else:
                        payload = json.loads(response.read())
            return normalize_rag_payload(payload)
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return EvidenceResult(error=f"RAG unavailable ({type(exc).__name__}); evidence not verified", refused=True)
