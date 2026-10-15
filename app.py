"""웹 실행: streamlit run app.py
서버를 먼저 띄우면(uvicorn services.api:app --port 8000) 서버를 통해, 아니면 프로세스 안에서 바로 실행된다."""
from ui.dashboard import main

main()
