"""규칙으로 확정한 사실을 LLM이 문장으로 다듬는다. 숫자 판단은 LLM에 맡기지 않는다."""
from __future__ import annotations

from .factory import get_llm
from .guard import is_grounded

SYSTEM = (
    "당신은 급성 심부전 환자를 보는 {role} 전문의 보조 AI입니다. "
    "아래 '확정된 사실'만 근거로, 의사에게 보여줄 한국어 요약 bullet을 정확히 {n}개 작성하세요. "
    "사실에 없는 수치나 진단을 만들지 마세요. 각 줄은 '- '로 시작하고 40자 이내로 쓰세요."
)


def narrate(role: str, facts: list[str], fallback: list[str], n: int = 3) -> list[str]:
    """규칙으로 확정한 사실(facts)을 LLM이 문장으로 다듬는다. 숫자 판단은 LLM에 맡기지 않는다.

    LLM이 없거나 실패하면 fallback 을 그대로 쓴다 (시연 중 네트워크 장애 대비).
    """
    llm = get_llm()
    if llm is None:
        return fallback
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        prompt = ChatPromptTemplate.from_messages(
            [("system", SYSTEM), ("human", "확정된 사실:\n{facts}")]
        )
        chain = prompt | llm | StrOutputParser()
        text = chain.invoke({"role": role, "n": n, "facts": "\n".join(f"- {f}" for f in facts)})
        lines = [l.strip().lstrip("-•* ").strip() for l in text.splitlines() if l.strip()]
        lines = lines[:n]
        if not lines or not is_grounded(lines, facts):
            return fallback  # 근거에 없는 숫자가 나오면 규칙 문장으로 대체 (Self-RAG 아이디어)
        return lines
    except Exception as e:  # noqa: BLE001  시연 안정성이 우선
        return fallback + [f"(LLM 호출 실패로 규칙 기반 요약 사용: {type(e).__name__})"]
