# HF-PathGuard 🫀🤖

**Safety-aware Multi-Agent Clinical Decision Support Prototype for Acute Heart Failure**

This is a **synthetic-data hackathon MVP**: input precheck → conditional parallel Mini specialists, RAG and similarity → deterministic safety rules → Mini Safety Chain → conditional Chief Large summary → Streamlit dashboard. It is **not a validated medical device** and does not deliver treatment or SMS.

The **Token-Efficient (A)** graph contains two real LangGraph conditional edges:

- If at least three of seven essential inputs are absent, it returns `INSUFFICIENT_DATA` without calling any LLM, RAG or similarity tool.
- Otherwise three Mini specialists run in parallel with RAG and similarity. Deterministic rules review the result. A Mini Safety Chain may **add** review warnings, but never remove rule warnings.
- If the combined status is `OK`, skip Chief Large. For `REVIEW`, Chief Large produces a short cautious summary. A Chief failure keeps a conservative fallback; the safety status never depends on Chief text.
- Both model tiers default to local `mock`. The optional single-LLM baseline is a separate explicitly selected comparison, not part of token-efficient routing.

## Run locally

```bash
uv sync
uv run pytest -q
uv run streamlit run app.py
```

The default `mock` mode needs no API keys and no network. `data/sample_patients.csv` contains fictional data only.

### 30-patient batch evaluation

Open **Batch Evaluation · Up to 30 Patients** below the main dashboard.
Choose the built-in 30 fictional test cases or upload 1–30 patients from CSV/JSON.
Click **Run Sequential Batch Evaluation**, then download the results CSV.

- This reuses the same `Pipeline.run`, one patient at a time, with no concurrent patient jobs.
- A failed patient does not cancel the remaining cases; only an error type is exported.
- Per-patient route/status, latency, Mini/Chief call counts and usage-metadata tokens are exported. `chief_route` means the Chief graph node ran, while `chief_used` means a real model response was received.
- No usage-metadata estimates are fabricated. Empty token cells mean the API did not provide complete usage or an inference failed.
- Mock mode does **not** establish clinical performance. For routing sensitivity/FNR, independent reference labels must be supplied to `evaluation/metrics.py`.
- Batch limit is 30 per run by design; CSV parsing separately supports up to 500 rows.

## Connect at the hackathon

Copy `.env.example` to `.env` locally. The organizer has announced `internal-api.khdp.net`, but the **exact path, model ID, request format, and authentication must be confirmed** on site using their khdp-api guidance.

| Module | Switch | Integration point |
|---|---|---|
| Chief Large | `LLM_PROVIDER=mock` or `openai_compatible`, `LLM_MODEL` | `llm/factory.py` |
| Mini specialists + Safety | `MINI_LLM_PROVIDER=mock` or `openai_compatible`, `MINI_LLM_MODEL` | `llm/factory.py` |
| RAG | `RAG_PROVIDER=mock` or `api` | `rag/adapter.py`, SSE `/api/ask` last `done` event |
| Similarity | `SIMILARITY_PROVIDER=mock` or `professor` | `similarity/adapter.py`, professor's Python function |

Remote patient-data transfer is disabled unless `ALLOW_REMOTE_DATA_TRANSFER=true` is explicitly set **after authorization**. Credentials and restricted data must never enter Git.

See [integration instructions](docs/integration.md). For the full output contract, inspect `data/schemas.py` (`FinalReport`).

For a lecture-by-lecture walkthrough and the recommended six-hour study order,
see [STUDY_ORDER.md](docs/STUDY_ORDER.md). The dashboard remains in English.

## Limitations

- All mock patient records and similarity scores are fictional; scores are not calibrated clinical probabilities.
- No fabricated literature citations: mock RAG returns no verified evidence.
- Safety validation flags missing or conflicting information; it is not a certified clinical rule set.
- Human clinical review is required. A notification draft is displayed but is **never sent**.
- The organizer's Jupyter environment cannot directly host Streamlit. On-site deployment through `khdp.ai Apps` is pending confirmation of its supported app format.
- The original `hf-agents_v01.ipynb` is preserved in your GitHub project; it was not among the uploaded lecture files and is not overwritten here.

## Project structure

```text
hf-pathguard/
├── app.py
├── agents/
│   ├── graph.py
│   ├── state.py
│   └── safety.py
├── config/
│   └── settings.py
├── data/
│   ├── schemas.py
│   ├── loader.py
│   └── sample_patients.csv
├── llm/
│   └── factory.py
├── rag/
│   └── adapter.py
├── similarity/
│   ├── adapter.py
│   └── mock_retriever.py
├── tools/
│   ├── clinical_tools.py
│   └── integration_tools.py
├── evaluation/
│   ├── baseline.py
│   ├── batch_runner.py
│   ├── demo_cases.py
│   └── metrics.py
├── services/
│   └── pipeline.py
├── ui/
│   ├── styles.py
│   └── assets/
│       └── dashboard_reference.png
├── tests/
│   ├── test_pipeline.py
│   ├── test_batch.py
│   ├── test_data.py
│   ├── test_rag.py
│   └── test_similarity.py
├── docs/
│   ├── STUDY_ORDER.md
│   └── integration.md
├── pyproject.toml
├── uv.lock
└── .env.example
```

The uploaded lectures informed this implementation: LangGraph StateGraph and parallel execution (2.1 and 2.7), LangChain LCEL/structured parsing (lessons 4–5), tools (LangGraph 3.2–3.3), and RAG interfaces (RAG 3.2). The remote evidence adapter does not itself implement the Chroma vector database from the RAG lesson. Human-in-the-loop interrupt, Self-RAG, and autonomous supervisor loops are not implemented; human review is represented by a safe report draft. The project deliberately avoids unbounded autonomous loops on shared infrastructure.
