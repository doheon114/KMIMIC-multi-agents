# 현장 연결 가이드 (데이터 · 유사환자 · RAG · 웹 · LLM)

모든 연결은 **파일 하나 + `.env` 한 줄**이다. 그래프와 화면은 손대지 않는다.
연결할 때마다 `python -m tests.smoke_test` → `python -m tests.test_api` 순서로 확인한다.
팀 코드에서 에러가 나도 시연은 멈추지 않는다 (유사환자는 "검색 실패"로 표시, RAG는 내장 가이드라인으로 대체).

## 0. 실행

```bash
pip install -r requirements.txt
cp .env.example .env                              # 처음엔 전부 mock
uvicorn services.api:app --port 8000              # 터미널 1: 서버 (http://localhost:8000/docs)
streamlit run app.py                              # 터미널 2: 웹
```

서버를 안 띄우면 웹이 같은 코드를 직접 실행한다 (화면 왼쪽 아래 "연결:"에 표시). 시연 중 서버가 죽어도 화면은 살아 있다.

## 1. 환자 데이터 (`data/`)

| 할 일 | 위치 |
|---|---|
| 데이터 파일 넣기 | `data/raw/파일.csv` (git에 안 올라감) |
| 컬럼명 맞추기 | `config/column_map.py` 의 `COLUMN_MAP` 왼쪽 값을 실제 컬럼명으로 |
| 단위/형식 변환 | 같은 파일 `TRANSFORMS` (예: Cr umol/L → mg/dL) |
| 켜기 | `.env`: `DATA_SOURCE=csv`, `DATA_PATH=data/raw/파일.csv` |

형식 예시는 `data/sample/patients_sample.csv`. 웹의 **K-MIMIC (Patient ID)** 탭에 환자 목록이 뜨면 성공.

## 2. 유사환자 네트워크 (`similarity/`)

1. 팀이 준 파이썬 파일을 `similarity/` 에 넣는다.
2. `similarity/team_adapter.py` 의 TODO 2곳: 모델 로드, 결과를 `SimilarCase(case_id, similarity, key_features, outcome)` 로 변환.
3. `.env`: `SIMILAR_BACKEND=team`

`outcome` 값이 "반응 개선"이면 Chief 신뢰도 계산에 반영된다. 팀 결과 표현이 다르면 `agents/evidence.py` 의 `"반응 개선"` 비교 한 줄만 고친다.

## 3. RAG (`rag/`)

1. `rag/team_adapter.py` 에서 경우 A(Chroma 폴더), B(함수), C(API 서버) 중 하나를 골라 TODO 2곳을 채운다.
   경우 A는 **DB 만들 때 쓴 임베딩 모델과 같은 모델**을 써야 한다.
2. `.env`: `RAG_BACKEND=team`
3. 검색이 엉뚱하면 `rag/pipeline.py` 의 `KEYWORD_DICT` 에 RAG 팀 문서 용어를 추가한다 (강의 3.6 키워드 사전).

검색어는 웹 "실행 로그"에서 볼 수 있다. 결과가 0건이면 자동으로 내장 가이드라인이 뜨고 결과 카드에 "(내장 가이드라인)"이라고 표시된다.

## 4. 웹 (`services/api.py`, `ui/`)

- 다른 웹 프론트(React, HTML 등)를 붙일 때는 `services/api.py` 상단의 엔드포인트만 쓰면 된다. CORS 열려 있음.
- 에이전트 카드가 실시간으로 켜지는 효과는 `POST /api/analyze/stream` (Server-Sent Events).
- 의사 승인은 `POST /api/review/{thread_id}` 에 `{"action": "approve|edit|reject", "sms": "..."}`.

```bash
curl -X POST localhost:8000/api/analyze -H 'Content-Type: application/json' -d '{"patient_id":"P-001"}'
```

## 5. LLM (`llm/`)

`.env`: `LLM_PROVIDER=openai | upstage | ollama`. 새 모델은 `llm/factory.py` 의 `PROVIDERS` 에 함수 하나 추가.
LLM은 요약 문장만 쓰고, 문장에 근거 없는 숫자가 들어가면 자동으로 버린다 (`llm/guard.py`).
`AGENT_MODE=react` 이면 Nephrology 가 도구(`tools/clinical_tools.py`)를 스스로 호출하는 에이전트로 동작한다.

## 6. 평가

`python -m evaluation.run_eval` → Multi-Agent 정확도. 실제 LLM 연결 시 Single LLM 비교도 같이 나온다.
대회 데이터 정답은 `evaluation/labels.csv` (`patient_id, expected_status, expected_response`).

## 강의 꿀팁 → 코드 위치

| 강의 | 꿀팁 | 적용 위치 |
|---|---|---|
| RAG 3.1.x | 인터페이스는 같고 클래스만 교체 | `llm/factory.py` `PROVIDERS` |
| RAG 3.2 / 3.4 | 벡터DB는 persist 로 재사용, 임베딩 바꾸면 인덱스 재생성 | `rag/ingest.py`, `rag/team_adapter.py` |
| RAG 3.5 · LG 2.2 | 표는 마크다운으로, .md 는 TextLoader 로 읽어 표 유지 | `rag/ingest.py` |
| RAG 3.6 | 키워드 사전으로 질문을 문서 용어로 재작성 | `rag/pipeline.py`, 약물 사전 `tools/clinical_rules.py` |
| RAG 4.x | Streamlit session_state, 스트리밍 | `ui/dashboard.py` |
| RAG 5.1 · LG 4.2 | 정답셋 먼저, 수치로 비교 | `evaluation/run_eval.py` |
| LG 2.1 / 2.2 | 노드는 state 받고 바뀐 dict 만 반환 | `agents/specialists.py` |
| LG 2.3 | conditional_edge, 문서 관련성 판단 | `agents/safety.py`, `rag/pipeline.py` `grade` |
| LG 2.4 Self-RAG | 답변이 근거에 기반했는지 검증 | `llm/guard.py` |
| LG 2.5 CRAG | 검색 실패 시 교정 경로 | `rag/pipeline.py` fallback |
| LG 2.7 | fan-out/fan-in 병렬, reducer 필수 | `agents/graph.py`, `agents/state.py` |
| LG 2.8 · 3.7 | supervisor 가 결과 종합 | `agents/chief.py` |
| LG 3.2~3.4 · 3.8 | @tool, docstring 과 인자 이름이 LLM 설명서 | `tools/clinical_tools.py`, `agents/tool_agent.py` |
| LG 3.5 | checkpointer + thread_id | `services/runner.py` |
| LG 3.6 | interrupt + Command(resume) 로 사람 승인 | `agents/safety.py` `human_review` |
