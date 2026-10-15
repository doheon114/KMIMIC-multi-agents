"""mock 근거 검색: 가이드라인/논문 요약 8개를 태그 겹침으로 점수화. RAG 팀 retriever 로 교체 예정.

요약은 데모용 의역이다. 발표 전에 원문과 대조하거나 RAG 팀 원문 청크로 교체할 것.
"""
from __future__ import annotations

from data.schema import EvidenceDoc

# 요약은 데모용 의역이다. 발표 전에 RAG 팀 원문 청크로 교체하거나 원문과 대조할 것.
_CORPUS: list[tuple[set[str], EvidenceDoc]] = [
    ({"diuretic", "response", "dose", "urine", "poor", "borderline"}, EvidenceDoc(
        title="ESC 2021 Heart Failure Guideline", source="Guideline", year=2021,
        snippet="울혈이 있으면 loop 이뇨제 권고. 투여 후 2시간 spot urine Na, 첫 6시간 소변량으로 조기 반응 평가, 불충분하면 용량 2배.",
        url="https://doi.org/10.1093/eurheartj/ehab368")),
    ({"diuretic", "response", "resistance", "poor", "urine", "sodium", "combination"}, EvidenceDoc(
        title="Use of diuretics in HF with congestion (HFA position statement)", source="Guideline", year=2019,
        snippet="spot urine Na < 50~70 mmol/L 또는 소변량 < 100~150 mL/h 이면 반응 불충분. 단계적 용량 증량과 병용요법 제시.",
        url="https://doi.org/10.1002/ejhf.1369")),
    ({"dose", "high", "renal", "poor"}, EvidenceDoc(
        title="DOSE trial: Diuretic strategies in ADHF", source="PubMed", year=2011,
        snippet="bolus와 지속주입, 저용량과 고용량(경구의 2.5배) 비교에서 주요 결과 차이 없음. 고용량은 울혈 해소 경향, 일시적 신기능 악화.",
        url="https://doi.org/10.1056/NEJMoa1005419")),
    ({"combination", "resistance", "poor", "acetazolamide"}, EvidenceDoc(
        title="ADVOR: Acetazolamide in ADHF with volume overload", source="PubMed", year=2022,
        snippet="loop 이뇨제에 acetazolamide 추가 시 3일 내 성공적 울혈 해소 비율 증가.",
        url="https://doi.org/10.1056/NEJMoa2203094")),
    ({"combination", "resistance", "poor", "hypokalemia", "thiazide"}, EvidenceDoc(
        title="CLOROTIC: Hydrochlorothiazide added to furosemide", source="PubMed", year=2023,
        snippet="HCTZ 추가로 체중 감소 등 이뇨 반응 개선, 저칼륨혈증과 신기능 악화는 더 흔함.",
        url="https://doi.org/10.1093/eurheartj/ehac689")),
    ({"aki", "renal", "creatinine", "egfr_lt30"}, EvidenceDoc(
        title="KDIGO Clinical Practice Guideline for AKI", source="Guideline", year=2012,
        snippet="48시간 내 Cr 0.3 mg/dL 이상 상승 또는 7일 내 기저치 1.5배 이상이면 AKI.",
        url="https://kdigo.org/guidelines/acute-kidney-injury/")),
    ({"hyperkalemia", "mra", "raas"}, EvidenceDoc(
        title="ESC 2021 HF: MRA/RAAS 억제제 사용 시 칼륨 관리", source="Guideline", year=2021,
        snippet="K 5.5 초과 시 MRA 감량, 6.0 초과 시 중단 고려 등 칼륨과 신기능 모니터링 권고 (원문 확인 필요).",
        url="https://doi.org/10.1093/eurheartj/ehab368")),
    ({"sglt2i", "good", "renal"}, EvidenceDoc(
        title="EMPULSE: Empagliflozin in hospitalized acute HF", source="PubMed", year=2022,
        snippet="입원 급성 심부전에서 empagliflozin 시작 시 90일 임상적 이득 증가.",
        url="https://doi.org/10.1038/s41591-021-01659-1")),
]


class MockEvidenceRetriever:
    """태그 겹침 개수로 점수 매기는 가짜 검색기. RAG 강의의 retriever.invoke() 자리."""

    def search(self, query: str, k: int = 3) -> list[EvidenceDoc]:
        words = set(query.lower().replace(",", " ").split())
        scored = sorted(_CORPUS, key=lambda t: len(t[0] & words), reverse=True)
        return [doc for tags, doc in scored[:k] if tags & words] or [_CORPUS[0][1]]
