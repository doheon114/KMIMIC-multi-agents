"""Workflow metrics require external labels; do not invent clinical ground truth."""
from collections.abc import Mapping, Sequence

def routing_metrics(rows: Sequence[Mapping], expected: Mapping[str, str]) -> dict:
    allowed = {"OK", "REVIEW", "INSUFFICIENT_DATA"}
    paired = [(expected[r["patient_id"]], r["overall_status"])
              for r in rows if r.get("execution_status") == "COMPLETED"
              and r.get("patient_id") in expected
              and expected[r["patient_id"]] in allowed and r.get("overall_status") in allowed]
    review = [(truth, pred) for truth, pred in paired if truth == "REVIEW" and pred in {"REVIEW", "OK"}]
    missing = [(truth, pred) for truth, pred in paired if truth == "INSUFFICIENT_DATA"]
    def ratio(a, b):
        return a / b if b else None
    return {
        "paired_count": len(paired),
        "routing_accuracy": ratio(sum(a == b for a, b in paired), len(paired)),
        "review_sensitivity": ratio(sum(b == "REVIEW" for _, b in review), len(review)),
        "review_false_negative_rate": ratio(sum(b == "OK" for _, b in review), len(review)),
        "abstention_accuracy": ratio(sum(b == "INSUFFICIENT_DATA" for _, b in missing), len(missing)),
    }
