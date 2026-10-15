from data.loader import load_sample
from similarity.mock_retriever import find_similar_patients

def test_mock_top_five_and_bounded_score():
    matches = find_similar_patients(load_sample(), top_k=5)
    assert len(matches) == 5
    assert all(0 < item.similarity_score <= 1 for item in matches)
