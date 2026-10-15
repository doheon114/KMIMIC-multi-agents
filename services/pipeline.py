"""Stable function callable by Streamlit, CLI or an organizer-provided app runtime."""
from time import perf_counter
from collections.abc import Callable
from config.settings import Settings
from data.schemas import FinalReport, PatientInput
from agents.graph import build_graph
from llm.factory import LLMClient
from rag.adapter import EvidenceAdapter
from similarity.adapter import SimilarityAdapter

class Pipeline:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.llm = LLMClient(self.settings)
        self.graph = build_graph(self.llm, EvidenceAdapter(self.settings), SimilarityAdapter(self.settings))

    def run(self, patient: PatientInput, on_progress: Callable[[str, str], None] | None = None) -> FinalReport:
        started = perf_counter()
        final_data = None
        # LangGraph emits node updates at superstep boundaries. In this graph the
        # first five branches are parallel, then safety and final run in sequence.
        for update in self.graph.stream(
            {"patient": patient.model_dump(mode="json")}, stream_mode="updates"
        ):
            for node, values in update.items():
                if on_progress:
                    on_progress(node, "completed")
                if node == "final":
                    final_data = values.get("final")
        if final_data is None:
            raise RuntimeError("The graph did not produce a final report")
        report = FinalReport.model_validate(final_data)
        report.execution_time_seconds = round(perf_counter() - started, 3)
        return report
