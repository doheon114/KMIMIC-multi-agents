import csv
import io
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from config.settings import Settings
from data.schemas import PatientInput
from services.pipeline import Pipeline

MAX_BATCH = 30

@dataclass
class BatchResult:
    records: list[dict]

    def csv_bytes(self) -> bytes:
        output = io.StringIO()
        fields = ["patient_id", "execution_status", "overall_status", "latency_seconds",
                  "mini_calls", "chief_calls", "chief_route", "chief_used", "input_tokens", "output_tokens",
                  "total_tokens", "review_reason_count", "missing_fields", "error"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(self.records)
        return output.getvalue().encode("utf-8-sig")

def run_batch(patients: Iterable[PatientInput], settings: Settings | None = None,
              on_progress: Callable[[int, int, dict], None] | None = None,
              pipeline_factory: Callable[[Settings], Pipeline] = Pipeline) -> BatchResult:
    items = list(patients)
    if not 1 <= len(items) <= MAX_BATCH:
        raise ValueError(f"Select 1–{MAX_BATCH} patients per batch")
    if len({p.patient_id for p in items}) != len(items):
        raise ValueError("Duplicate patient IDs are not supported in a batch")
    settings = settings or Settings.from_env()
    records = []

    for index, patient in enumerate(items, start=1):
        row = {"patient_id": patient.patient_id, "execution_status": "FAILED",
               "overall_status": "", "latency_seconds": "", "mini_calls": "",
               "chief_calls": "", "chief_route": "", "chief_used": "", "input_tokens": "", "output_tokens": "",
               "total_tokens": "", "review_reason_count": "", "missing_fields": "", "error": ""}
        try:
            pipeline = pipeline_factory(settings)
            chief_called = False
            def capture(node: str, state: str) -> None:
                nonlocal chief_called
                if node == "chief" and state == "completed":
                    chief_called = True
            report = pipeline.run(patient, on_progress=capture)
            mini_usage = pipeline.mini_llm.usage_snapshot()
            chief_usage = pipeline.llm.usage_snapshot()
            calls = mini_usage["calls"] + chief_usage["calls"]
            known_usage = calls and all(
                usage["total_tokens"] is not None
                for usage in (mini_usage, chief_usage) if usage["calls"]
            )
            row.update(execution_status="COMPLETED", overall_status=report.overall_status,
                       latency_seconds=report.execution_time_seconds,
                       mini_calls=mini_usage["calls"], chief_calls=chief_usage["calls"],
                       chief_route="YES" if chief_called else "NO",
                       chief_used="YES" if chief_usage["calls"] > 0 else "NO",
                       input_tokens=sum(u["input_tokens"] for u in (mini_usage, chief_usage) if u["calls"]) if known_usage else "",
                       output_tokens=sum(u["output_tokens"] for u in (mini_usage, chief_usage) if u["calls"]) if known_usage else "",
                       total_tokens=sum(u["total_tokens"] for u in (mini_usage, chief_usage) if u["calls"]) if known_usage else "",
                       review_reason_count=len(report.review_reasons),
                       missing_fields="; ".join(report.missing_fields))
            # If no model was called, actual token usage is exactly zero.
            if calls == 0:
                row.update(input_tokens=0, output_tokens=0, total_tokens=0)
        except Exception as exc:
            # No patient content or credentials in the export.
            row["error"] = type(exc).__name__
        records.append(row)
        if on_progress:
            on_progress(index, len(items), row.copy())
    return BatchResult(records=records) # record
