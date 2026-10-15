"""★ 현장에서 여기만 채운다: 유사환자 팀 코드 연결.

1) 팀이 준 파이썬 파일을 similarity/ 폴더에 넣는다 (예: similarity/network.py)
2) 아래 TODO 두 곳을 채운다
3) .env 에 SIMILAR_BACKEND=team
4) python -m tests.smoke_test 로 확인
"""
from __future__ import annotations

from data.schema import Patient, SimilarCase


class TeamSimilarFinder:
    def __init__(self):
        # TODO 1: 팀 모델/네트워크/임베딩 로드
        # from .network import load_model
        # self.model = load_model("data/raw/similarity_model.pkl")
        raise NotImplementedError("similarity/team_adapter.py 의 TODO 를 채워주세요")

    def find(self, patient: Patient, k: int = 5) -> list[SimilarCase]:
        # TODO 2: 팀 코드 호출 결과를 SimilarCase 로 변환
        # features = patient.model_dump()            # 팀 코드가 dict/DataFrame 을 받으면 그대로
        # rows = self.model.query(features, top_k=k)  # 예: [{"id":..., "score":..., "outcome":...}]
        # return [SimilarCase(case_id=str(r["id"]), similarity=round(float(r["score"]), 2),
        #                     key_features=r.get("desc", ""), outcome=r["outcome"]) for r in rows]
        raise NotImplementedError
