"""Settings: remote model/API calls require explicit authorization."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv

def _bool(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}

@dataclass(frozen=True)
class Settings:
    llm_provider: str = "mock"
    llm_model: str = "demo"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_timeout_seconds: float = 25.0
    llm_max_concurrent_calls: int = 1
    mini_llm_provider: str = "mock"
    mini_llm_model: str = "demo-mini"
    mini_llm_base_url: str = ""
    mini_llm_api_key: str = ""
    allow_remote_data_transfer: bool = False
    rag_provider: str = "mock"
    rag_ask_url: str = ""
    rag_api_key: str = ""
    rag_timeout_seconds: float = 15.0
    similarity_provider: str = "mock"
    similarity_module: str = "similarity.snf_retriever"
    similarity_function: str = "find_similar_patients"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(override=False)
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "mock").strip().lower(),
            llm_model=os.getenv("LLM_MODEL", "demo"),
            llm_base_url=os.getenv("LLM_BASE_URL", ""),
            llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("KHDP_API_KEY", ""),
            llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "25")),
            llm_max_concurrent_calls=max(1, int(os.getenv("LLM_MAX_CONCURRENT_CALLS", "1"))),
            mini_llm_provider=os.getenv("MINI_LLM_PROVIDER", "mock").strip().lower(),
            mini_llm_model=os.getenv("MINI_LLM_MODEL", "demo-mini"),
            mini_llm_base_url=os.getenv("MINI_LLM_BASE_URL", ""),
            mini_llm_api_key=os.getenv("MINI_LLM_API_KEY") or os.getenv("KHDP_API_KEY", ""),
            allow_remote_data_transfer=_bool("ALLOW_REMOTE_DATA_TRANSFER"),
            rag_provider=os.getenv("RAG_PROVIDER", "mock").strip().lower(),
            rag_ask_url=os.getenv("RAG_ASK_URL", ""),
            rag_api_key=os.getenv("RAG_API_KEY", ""),
            rag_timeout_seconds=float(os.getenv("RAG_TIMEOUT_SECONDS", "15")),
            similarity_provider=os.getenv("SIMILARITY_PROVIDER", "mock").strip().lower(),
            similarity_module=os.getenv("SIMILARITY_MODULE", "similarity.snf_retriever"),
            similarity_function=os.getenv("SIMILARITY_FUNCTION", "find_similar_patients"),
        )

    def require_remote_authorization(self) -> None:
        if not self.allow_remote_data_transfer:
            raise PermissionError("Remote patient-data transfer is disabled; obtain authorization first.")
