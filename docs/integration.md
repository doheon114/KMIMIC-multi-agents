# HF-PathGuard — integration day checklist

## 0. Boundary

Only synthetic or explicitly authorized data may be loaded. Do **not** upload real clinical records to personal GitHub or public hosting. The announced KHDP internal LLM domain does not imply an OpenAI-compatible API path or authentication method; first inspect their `khdp-api` documentation from inside the event environment. `khdp.ai Apps` hosting contract is still unknown; do not assume Jupyter can expose Streamlit.

## 1. Boot & branches

```bash
uv sync
uv run pytest -q
uv run streamlit run app.py
```

Import the code under the existing repo `KMIMIC-multi-agents` on your chosen feature branch; **do not overwrite** the existing notebook or assets. Open a pull request into `develop` after tests pass. These commands are for a local machine or an allowed app runtime, not the organizer's Jupyter host.

## 2. LLM endpoint

`.env` (never commit):

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://CONFIRMED-ENDPOINT/v1
LLM_MODEL=CONFIRMED_MODEL_ID
LLM_API_KEY=SECRET
ALLOW_REMOTE_DATA_TRANSFER=true
LLM_MAX_CONCURRENT_CALLS=1
```

Confirm API-compatible request/response first with **non-patient test text**. If incompatible, add a backend to `llm/factory.py` with the same `specialist(kind, patient)` and `text(system, user)` methods. For safety, remote model errors return `needs_review=True`, not plausible clinical output. Turn off remote transfer if policy does not permit sending the entered data.

## 3. RAG team API

Expected (subject to confirmation): `POST /api/ask`, body `{"question": "..."}`, content type `text/event-stream`. Last frame:

```text
event: done
data: {"answer":"...","cited":[],"refused":false,"passages":[]}
```

Enable `RAG_PROVIDER=api`, `RAG_ASK_URL=.../api/ask`; adapt request keys and authentication in `rag/adapter.py` **only** after team confirms. `evidence_found` stays false until independent source/citation verification is defined; do not call returned citations validated evidence.

## 4. Professor similarity Python code

Place the authorized code, e.g. `similarity/professor_impl.py`, in the approved runtime and expose:

```python
def find_similar_patients(patient: dict, top_k: int = 5) -> list[dict]:
    # output: [{"patient_id":"...", "similarity_score":0.85,
    #           "key_features":[], "observed_outcome":None}, ...]
    ...
```

Configure `SIMILARITY_PROVIDER=professor`, `SIMILARITY_MODULE=similarity.professor_impl`. Keep the reference cohort/model assets in the authorized environment; do not commit restricted assets. Confirm score definition, features, missing-value handling, cohort isolation, and leakage checks.

## 5. Dataset mapping

The CSV/JSON loader expects one patient snapshot per row. It supports aliases in `data/loader.py`; extend `ALIASES` when organizers publish columns. Missing measurements stay `None`. Explicit numeric unit conversion and longitudinal time-series loader will be needed if real K-MIMIC tables are supplied. Do not treat the 6-hour urine value as a complete treatment-response label without timing and context.

## 6. Safety + evaluation

- Single LLM and Multi-Agent use the same patient input, but the proposed system has multiple calls and external tools. Report cost/latency separately; do not claim pure orchestration effects without ablations.
- Log only aggregate elapsed time/model info in any sharable artifact; avoid patient data in logs.
- `notification_draft` is a text preview, not sent. Actual SMS requires authorization, recipient review, and a separate explicit confirmation workflow.
- `overall_status` is a demonstration review flag, **not a medical decision**.

## 7. Notebook references used

Your tutorials informed the structure: StateGraph nodes (LangGraph 2.1), parallel fan-in (2.7), ChatPromptTemplate and LCEL (LangChain basics 4–5), custom @tool interfaces (LangGraph 3.2–3.3), and an external RAG adapter (RAG 3.2, adapted rather than copied). Full Self-RAG, Corrective RAG, human-in-the-loop interrupts, and supervisor routing are not implemented. Deterministic safety decisions remain outside LLM output.
