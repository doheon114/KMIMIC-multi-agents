# basic LLM versus our model

import json
from time import perf_counter
from data.schemas import PatientInput
from llm.factory import LLMClient

def run_baseline(patient: PatientInput, llm: LLMClient) -> dict[str, object]:
    started = perf_counter()
    if llm.is_mock:
        response = "Mock single-model baseline: input received; no clinical inference performed."
    else:
        prompt = ("Give a cautious observational summary of the provided synthetic case. "
                  "Identify missing data; do not make treatment recommendations. "
                  "Reply in four sentences or fewer.")
        try:
            response = llm.text(prompt, json.dumps(patient.model_dump(mode="json"), ensure_ascii=False))
        except Exception as exc:
            response = f"Baseline model unavailable ({type(exc).__name__}); no inference performed."
    return {"answer": response, "duration_seconds": round(perf_counter()-started, 3),
            "provider": llm.settings.llm_provider, "model": llm.settings.llm_model}
