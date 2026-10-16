import json
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from data.schemas import PatientInput, SpecialistResult
from llm.factory import LLMClient, _json_object, mock_specialist, normalize_specialist
from tools.clinical_tools import clinical_features
from tools.pharmacy_tools import make_pharmacy_tools

MAX_ROUNDS = 3
# System Prompt
SYSTEM = (
    "You are the pharmacy reviewer in an unvalidated clinical research demonstration. "
    "You have tools: check_drug_interactions, check_renal_dosing, check_electrolytes. "
    "Call only the tools you need (they take no arguments and read the patient record themselves). "
    "Do not prescribe, change doses, or infer missing values. "
    "When done, return ONLY JSON with agent, assessment, concern_level (low/moderate/high/unknown), "
    "confidence (low/moderate/high/unknown), needs_review (boolean), reason (string)."
)
FINALIZE = "Tool budget reached. Do not call more tools; return the final JSON now."


class ScriptedPharmacyModel:
    """Deterministic stand-in for LLM_PROVIDER=mock: picks tools by simple rules, then answers."""
    def __init__(self, patient: PatientInput):
        self.patient = patient

    # choose the tools to call
    def invoke(self, messages, tools=True) -> AIMessage:
        if tools and not any(isinstance(m, ToolMessage) for m in messages):
            p, calls = self.patient, []
            if p.medication_history:
                calls.append("check_drug_interactions")
            if p.creatinine is not None:
                calls.append("check_renal_dosing")
            if p.potassium is not None or p.sodium is not None:
                calls.append("check_electrolytes")
            if calls:
                return AIMessage(content="", tool_calls=[
                    {"name": n, "args": {}, "id": f"mock-{i}", "type": "tool_call"} for i, n in enumerate(calls)])
        return AIMessage(content=mock_specialist("pharmacy", self.patient).model_dump_json())


def build_pharmacy_graph(mini: LLMClient, patient: PatientInput): # mini: small LLM
    tool_list = make_pharmacy_tools(patient)
    tool_node = ToolNode(tool_list)
    if mini.is_mock:
        scripted = ScriptedPharmacyModel(patient) # remember the patients
        llm_with_tools, llm_without_tools = (lambda m: scripted.invoke(m, True)), (lambda m: scripted.invoke(m, False))
    else:
        llm_with_tools, llm_without_tools = (lambda m: mini.chat(m, tool_list)), (lambda m: mini.chat(m))

# new version : 도구 호출 및 환자 정보 load 기억
    def agent(state: MessagesState) -> MessagesState:
        messages = state["messages"]
        rounds = sum(1 for m in messages if isinstance(m, AIMessage) and m.tool_calls)
        if rounds >= MAX_ROUNDS:  # tool budget used up: answer without tools
            return {"messages": [llm_without_tools([*messages, HumanMessage(content=FINALIZE)])]}
        return {"messages": [llm_with_tools(messages)]}

    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("agent", agent)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges("agent", tools_condition)  # tool_calls -> "tools", else END
    graph_builder.add_edge("tools", "agent")
    return graph_builder.compile()


def run_pharmacy_agent(mini: LLMClient, patient: PatientInput) -> tuple[SpecialistResult, list[str]]:
    start = [SystemMessage(content=SYSTEM), HumanMessage(content=json.dumps(
        {"patient": patient.model_dump(mode="json"), "observations": clinical_features(patient)}, ensure_ascii=False))]
    messages = start
    try:
        messages = build_pharmacy_graph(mini, patient).invoke({"messages": start})["messages"]
        result = normalize_specialist("pharmacy", _json_object(str(messages[-1].content)))
    except Exception:
        result = mini.specialist("pharmacy", patient)  # previous non-tool behaviour
    called, findings = tool_trace(messages)
    return merge_tool_findings(result, called, findings), called


# Trace which tool were called ! important for medical review
def tool_trace(messages) -> tuple[list[str], list[str]]:
    """Which tools ran and which flags they raised, read from the ToolMessages."""
    called, findings = [], []
    for m in messages:
        if isinstance(m, ToolMessage):
            called.append(m.name)
            try:
                findings.extend(json.loads(m.content).get("flags", []))
            except (TypeError, ValueError, AttributeError):
                pass
    return called, findings

# 도구가 경고 발견하면 > review true로 바꾸는 안전장치
def merge_tool_findings(result: SpecialistResult, called: list[str], findings: list[str]) -> SpecialistResult:
    """Tool flags can only escalate: the model cannot clear a deterministic finding."""
    unique = list(dict.fromkeys(findings))
    if unique:
        result.needs_review = True
        if result.concern_level in {"low", "unknown"}:
            result.concern_level = "moderate"
        if result.assessment == "No flag in synthetic review":
            result.assessment = "Concern noted"
        result.reason += " Tool findings: " + "; ".join(unique) + "."
    result.reason += f" Tools used: {', '.join(dict.fromkeys(called)) or 'none'}."
    return result
