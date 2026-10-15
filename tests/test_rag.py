import pytest
from rag.adapter import last_done_payload, normalize_rag_payload

def test_last_done_event_only():
    lines = [
        'event: token', 'data: {"answer":"partial"}', '',
        'event: done', 'data: {"answer":"final", "cited":["ref-1"], "passages":[], "refused":false}', '',
    ]
    final = last_done_payload(lines)
    evidence = normalize_rag_payload(final)
    assert evidence.summary == "final"
    assert evidence.citations == [{"text":"ref-1"}]
    assert evidence.evidence_found is False  # still must be independently checked

def test_no_done_is_error():
    with pytest.raises(ValueError):
        last_done_payload(['event: token', 'data: {"answer":"partial"}', ''])

def test_refused_has_no_summary():
    result = normalize_rag_payload({"answer":"unsafe", "refused":True})
    assert result.summary == "" and result.refused
