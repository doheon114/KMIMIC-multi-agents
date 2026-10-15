# HF-PathGuard — 강의 기반 6시간 학습·개발 가이드

이 문서는 업로드한 세 강의 저장소의 **실제 노트북 제목과 코드 패턴**을 기준으로 작성했습니다.
영어 UI는 유지합니다. 의료 분석은 연구용 합성 데이터로만 실습하세요.

## 먼저 이해할 전체 실행 흐름

`app.py` → `services/pipeline.py` → `agents/graph.py` → 병렬로 `llm/factory.py` (심장·신장·약물), `rag/adapter.py`, `similarity/adapter.py` → `agents/safety.py` → `FinalReport` → `app.py` 표시.

현재 구조는 **병렬 전문가 분석 후 안전성 검사**입니다. 강의 3.7의 Supervisor가 Agent를 반복적으로 선택하는 구조는 아닙니다. 해커톤에서는 이 차이를 정확히 설명하세요.

## 6시간 실행 시간표

| 시간 | 목표 | 실제로 할 일 |
|---|---|---|
| 0:00–1:00 | 구조 이해 | LangGraph 2.1 → 2.7 예제 실행, `state.py` 및 `graph.py` 대응 확인 |
| 1:00–2:30 | 코드 고정 | `llm/factory.py`, `integration_tools.py`, RAG·유사 환자 Adapter 확인, Mock 결과 점검 |
| 2:30–3:30 | 검증 | `uv sync`, `uv run pytest -q`, `uv run streamlit run app.py`, 입력·오류·보고서 확인 |
| 3:30–4:00 | GitHub 고정 | `.env`, 개인정보, 대용량 데이터 제외. 팀 브랜치로 커밋 후 검증된 커밋을 공유 |
| 4:00–5:30 | 강의 집중 수강 | LangChain 기초 4·5, LangGraph 3.2·3.3, RAG 3.2를 실제 코드와 대조 |
| 5:30–6:00 | 설명 연습 | 아래 10개 질문을 소리 내어 답하기 |

처음부터 37개 노트북을 모두 시청하려고 하지 마세요. 지금 프로젝트에 직접 쓰이는 7~8개만 우선합니다.

## 파일별 추천 공부 순서

| 순서 | 파일 | 추천 강의 | 연결되는 코드 개념 |
|---|---|---|---|
| 1 | `data/schemas.py` | LangChain 기초 **4. 답변의 형식을 컨트롤하는 방법** | Pydantic `BaseModel`, `Field`, 출력 검증 |
| 2 | `agents/state.py` | LangGraph **2.1 LangChain vs LangGraph** | `TypedDict` 기반 상태 정의 |
| 3 | `agents/graph.py` | LangGraph **2.1 → 2.7 병렬 처리** | `StateGraph`, `add_node`, `add_edge`, `START`, `END`, `compile` |
| 4 | `llm/factory.py` | LangChain 기초 **4 → 5. LCEL** / RAG **3.1 ChatOpenAI** | `ChatOpenAI`, `ChatPromptTemplate`, LCEL, `StrOutputParser`, Pydantic 검증 |
| 5 | `tools/integration_tools.py` | LangGraph **3.2 도구 활용 → 3.3 LangGraph 도구** | `@tool`, 도구 입력과 `.invoke()` |
| 6 | `rag/adapter.py` | RAG **3.2 LangChain과 Chroma**, **3.5 전처리**, **3.6 키워드 사전** | 근거 검색 입력·출력. 현재는 외부 SSE RAG API 연결이므로 Chroma 구현과 동일하지 않음 |
| 7 | `similarity/adapter.py`, `mock_retriever.py` | LangGraph **3.8 커스텀 도구** | 독립적인 Python 검색 함수를 Agent 도구로 연결 |
| 8 | `agents/safety.py` / `tools/clinical_tools.py` | LangGraph **3.6 human-in-the-loop** (개념 참고) | 사람이 검토할 경고 생성. 실제 `interrupt()`는 아직 없음 |
| 9 | `services/pipeline.py` | LangGraph **2.1 실행**, **3.3 stream** | 그래프 실행, `stream_mode="updates"`, 완료 이벤트 |
| 10 | `app.py` / `ui/styles.py` | 세 강의에 직접 대응 없음 | Streamlit UI, 상태바, 입력·보고서 출력 |
| 11 | `config/settings.py` / `.env.example` | RAG **3.1 환경 설정** | 환경 변수와 API 설정 분리 |
| 12 | `data/loader.py` | RAG **3.5 전처리** (아이디어만 참고) | CSV/JSON 정규화, 결측 처리. 임상 데이터 전처리는 별도 구현 |
| 13 | `evaluation/baseline.py` / `tests/` | RAG **5.1 LangSmith Evaluation** (확장 학습) | 간단한 Mock 검증·baseline. LangSmith 정식 평가는 구현되지 않음 |

## 구현 범위: 같은 점과 다른 점

### 강의 패턴을 직접 활용한 부분

- `AgentState` + `StateGraph(AgentState)` + `graph_builder.add_node(...)` + `graph_builder.add_edge(...)` + `compile()` — LangGraph 2.1, 2.7
- 동시에 실행되는 여러 Node의 결과를 모아 다음 단계로 연결 — LangGraph 2.7
- `ChatPromptTemplate | ChatOpenAI | StrOutputParser` — LangChain 기초 4–5
- `@tool`을 이용해 Python 함수를 도구로 등록 — LangGraph 3.2–3.3

### 강의를 응용하거나 별도 구현한 부분

- 전문의 세 명의 JSON 응답을 Pydantic으로 검증하고 위험시 추가 검토 요구
- RAG는 **팀의 별도 API**를 호출하고 SSE `done` 메시지를 읽음. Chroma를 프로젝트 안에 직접 만드는 강의 3.2와 구분할 것
- 유사 환자 검색은 교수님 구현을 `similarity/professor_impl.py` 형태로 끼워 넣을 수 있게 만든 인터페이스
- `Safety`는 LLM 추론이 아니라 코드 규칙을 활용하고 최종 진료 판단을 내리지 않음
- 로봇은 고정 이미지이며 상태바는 LangGraph 완료 이벤트로 갱신. 내부 토큰 진행률 73% 등은 계산하지 않음

### 현재 **구현하지 않은** 강의 기능

- LangGraph 3.7 Supervisor의 동적 라우팅 및 반복 선택
- LangGraph 3.6의 체크포인터 기반 `interrupt()` / `Command(resume=...)`
- Self-RAG(2.4), Corrective RAG(2.5)의 자동 평가·재검색 루프
- RAG 5.1의 LangSmith 평가, 자체 Chroma Vector DB

이 기능을 실제로 구현했다고 발표하지 마세요. 여유가 있다면 다음 단계로 확장 가능합니다.

## 현장 연결 지점 — 코드 고정 후 여기만 수정

1. **LLM:** `.env`의 `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` 확인 → `llm/factory.py`. API가 OpenAI 호환이 아닌 경우 다른 클라이언트 구현 필요.
2. **RAG:** `RAG_PROVIDER=api`, `RAG_ASK_URL` 확인 → `rag/adapter.py`. 팀 API의 실제 POST 형식, 인증, SSE 이벤트를 검증.
3. **유사 환자:** `SIMILARITY_PROVIDER=professor`, 교수님 함수 파일 경로 확인 → `similarity/adapter.py`. 점수 정의와 학습·평가 데이터 분리 확인.
4. **데이터:** 현장 컬럼명·단위·시점 확인 → `data/loader.py`. 시간축과 단위가 다른 경우 단순 이름 변경으로 처리하면 안 됨.
5. **실제 알림:** 현재 발송하지 않음. 의료진 승인·수신자 확인·데이터 사용 허가 전에는 SMS 연동 금지.

실제 환자 정보를 임의의 외부 LLM/RAG 서버에 전송하지 마세요. `.env`와 환자 원자료는 Git에 올리지 마세요.

## 서영이의 30분 설명 리허설: 핵심 10문항

1. `PatientInput`은 왜 Pydantic으로 정의했나?
2. `AgentState`와 `FinalReport`는 각각 무엇인가?
3. `StateGraph`와 `compile()`은 어떤 역할인가?
4. 5개 Agent가 어떻게 병렬 실행되며, 왜 Safety는 뒤에서 실행되는가?
5. `@tool`과 `.invoke()`는 무엇인가?
6. `ChatPromptTemplate | LLM | StrOutputParser`에서 `|`는 무엇인가?
7. RAG가 실제로 검색했다는 것과 출처가 검증되었다는 것은 왜 다른가?
8. 유사 환자의 similarity score를 임상 위험 확률이라고 부르면 안 되는 이유는?
9. `stream_mode="updates"`로 알 수 있는 것과 알 수 없는 것은?
10. 의료진 승인 없이 최종 보고서가 치료 권고나 실제 SMS로 이어지지 않는 이유는?

## 종료 조건

`uv run pytest -q` 통과 → `uv run streamlit run app.py` 실행 → Mock 환자 분석 완료 → 진행 상태바 완료 → 최종 보고서 JSON 확인 → 팀 공용 GitHub에 민감 데이터 없이 업로드. API와 교수님 함수는 현장에서 연결할 부분으로 명시합니다.
