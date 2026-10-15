"""환경 설정을 한 곳에서 읽는다. 무엇을 갈아끼울지는 전부 .env 로 정한다."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()      # mock | openai | upstage | ollama | ...
DATA_SOURCE = os.getenv("DATA_SOURCE", "mock").lower()        # mock | csv
DATA_PATH = ROOT / os.getenv("DATA_PATH", "data/raw/patients.csv")
RAG_BACKEND = os.getenv("RAG_BACKEND", "mock").lower()        # mock | team
SIMILAR_BACKEND = os.getenv("SIMILAR_BACKEND", "mock").lower()  # mock | team
MESSAGE_LOG = ROOT / "data" / "logs" / "message_log.jsonl"
