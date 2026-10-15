# HF-PathGuard 🫀🤖

**Safety-aware Multi-Agent Clinical Decision Support Prototype for Acute Heart Failure**

This is a **synthetic-data hackathon MVP**: CSV/manual patient input → LangGraph specialist assessments → RAG and similarity adapters → deterministic safety review → Streamlit dashboard. It is **not a validated medical device** and does not deliver treatment or SMS.

## Run locally

```bash
uv sync
uv run pytest -q
uv run streamlit run app.py
```

The default `mock` mode needs no API keys and no network. `data/sample_patients.csv` contains fictional data only.

## Connect at the hackathon

Copy `.env.example` to `.env` locally. The organizer has announced `internal-api.khdp.net`, but the **exact path, model ID, request format, and authentication must be confirmed** on site using their khdp-api guidance.

| Module | Switch | Integration point |
|---|---|---|
| LLM | `LLM_PROVIDER=mock` or `openai_compatible` | `llm/factory.py` |
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
app.py                    Streamlit UI
agents/                   LangGraph parallel nodes and safety synthesis
config/                   Settings and secret handling
data/                     Input/output schema, CSV/JSON loader, mock patient
llm/                      Mock and compatible API model adapter
rag/                      Mock and SSE evidence adapter
similarity/               Mock and professor function adapter
tools/                    Deterministic calculations
evaluation/               Single-LLM baseline
services/                 Pipeline runner and CLI demo
ui/                       Visual components
tests/                    Automated checks
```

The uploaded lectures informed this implementation: LangGraph StateGraph and parallel execution (2.1 and 2.7), LangChain LCEL/structured parsing (lessons 4–5), tools (LangGraph 3.2–3.3), and RAG interfaces (RAG 3.2). The remote evidence adapter does not itself implement the Chroma vector database from the RAG lesson. Human-in-the-loop interrupt, Self-RAG, and autonomous supervisor loops are not implemented; human review is represented by a safe report draft. The project deliberately avoids unbounded autonomous loops on shared infrastructure.
