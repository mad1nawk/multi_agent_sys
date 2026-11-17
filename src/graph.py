import json
import re
import threading
from typing import Annotated, List, TypedDict
from src.observability import logger, trigger_alert

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.context_loader import (
    build_planner_prompt,
    build_router_prompt,
    build_solver_prompt,
    build_verifier_prompt,
)
from src.memory import get_long_term_memory, get_short_term_checkpointer
from src.tools import PLANNER_TOOLS, SOLVER_TOOLS

# Initialization of Ollama models
llm_router = ChatOllama(model="gemma3:270m", temperature=0.0, num_predict=10, num_ctx=1024, keep_alive="5m")

llm_solver_with_tools = ChatOllama(
    model="qwen3.5:4b", temperature=0.1, num_predict=1000, num_ctx=2048, reasoning=False, keep_alive="5m"
).bind_tools(SOLVER_TOOLS)

llm_solver_text = ChatOllama(
    model="qwen3.5:4b", temperature=0.2, num_predict=1000, num_ctx=2048, reasoning=False, keep_alive="5m"
)

llm_planner_with_tools = ChatOllama(
    model="qwen3.5:4b", temperature=0.1, num_predict=1400, num_ctx=2048, reasoning=False, keep_alive="5m"
).bind_tools(PLANNER_TOOLS)

llm_planner_text = ChatOllama(
    model="qwen3.5:4b", temperature=0.2, num_predict=1400, num_ctx=2048, reasoning=False, keep_alive="5m"
)


llm_verifier = ChatOllama(model="granite4:3b", temperature=0.0, num_predict=150, num_ctx=1536, keep_alive="5m")
llm_chat = ChatOllama(model="qwen3.5:4b", temperature=0.3, num_predict=200, num_ctx=1024, keep_alive="5m")

mem0_client = get_long_term_memory()


# Graph working memory
class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    user_id: str
    route: str
    retrieved_notes: str
    evidence: List[str]
    draft: str
    verifier_verdict: str
    verifier_errors: List[dict]
    retries: int
    tool_calls_count: int


def _strip_think(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    return text.strip()

def router_node(state: AgentState) -> dict:
    print(">>> [1/5] ROUTER (Hybrid: Rule-Guard + gemma3:270m)...")
    last_user_msg = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
    lower_q = last_user_msg.lower()

    if any(w in lower_q for w in ["quiz", "test on", "make a test", "self-test", "flashcards", "questions"]):
        label = "QUIZ"
    elif any(w in lower_q for w in ["study plan", "schedule", "prepare for", "week plan"]):
        label = "PLAN"
    elif any(ch in lower_q for ch in "0123456789=+-*/^") or any(
        w in lower_q for w in ["solve", "compute", "calculate", "integral", "derivative", "limit"]
    ):
        label = "MATH"
    else:
        response = llm_router.invoke([
            SystemMessage(content=build_router_prompt()),
            HumanMessage(content=last_user_msg),
        ])
        label = response.content.strip().upper().strip(".")
        if label not in {"MATH", "THEORY", "PLAN", "QUIZ", "SMALLTALK"}:
            label = "THEORY"

    print(f"    Route selected: {label}")
    return {"route": label, "retries": 0, "verifier_errors": [], "evidence": [], "tool_calls_count": 0}


def retrieve_node(state: AgentState) -> dict:
    print(">>> [2/5] RETRIEVE (Mem0 search)...")
    last_user_msg = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
    user_id = state.get("user_id", "default_student")
    try:
        results = mem0_client.search(query=last_user_msg, filters={"user_id": user_id}, limit=3)
        memories = [r.get("memory", "") for r in results.get("results", [])] if isinstance(results, dict) else []
        notes_text = "\n".join(f"- {m}" for m in memories) if memories else "No specific memory notes found."
    except Exception as e:
        print(f"    Mem0 search skipped: {e}")
        notes_text = "No memory notes available."
    return {"retrieved_notes": notes_text}


def smalltalk_node(state: AgentState) -> dict:
    print(">>> [2/3] SMALLTALK...")
    last_user_msg = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
    res = llm_chat.invoke([
        SystemMessage(content=build_solver_prompt("SMALLTALK")),
        HumanMessage(content=last_user_msg),
    ])
    clean = _strip_think(res.content)
    return {"draft": clean, "messages": [AIMessage(content=clean)]}

def solver_node(state: AgentState) -> dict:
    used = state.get("tool_calls_count", 0)
    print(f">>> [3/5] SOLVER (qwen3.5:4b) | attempt {state.get('retries', 0) + 1} | tools used: {used}...")
    last_user_msg = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
    sys_prompt = build_solver_prompt(
        route=state["route"],
        retrieved_notes=state.get("retrieved_notes", ""),
        verifier_errors=state.get("verifier_errors", []),
    )

    if used == 0 and state["route"] == "MATH":
        fast_tool_prompt = (
            sys_prompt
            + "\n\nFirst, call the `calculator` tool to compute/verify the exact answer. "
            "Do NOT write Python code in your text response."
        )
        response = llm_solver_with_tools.invoke([
            SystemMessage(content=fast_tool_prompt),
            HumanMessage(content=last_user_msg),
        ])
    else:
        evidence_str = "\n".join(state.get("evidence", [])) or "No external tool output."
        user_payload = (
            f"Question: {last_user_msg}\n\n"
            f"Verified Tool Evidence:\n{evidence_str}\n\n"
            "STRICT RULES:\n"
            "1. Do NOT output any Python code or ```python blocks.\n"
            "2. Use $...$ for inline math and $$...$$ for block equations.\n"
            "3. Complete ALL sections: Problem, Method, Solution Steps, Verification, Answer, Check yourself."
        )
        response = llm_solver_text.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_payload),
        ])

    clean_text = _strip_think(response.content)
    if not getattr(response, "tool_calls", None) and not clean_text:
        clean_text = f"Verified result: {', '.join(state.get('evidence', []))}"

    print(f"    Solver draft length: {len(clean_text)} chars")
    return {"messages": [response], "draft": clean_text}


def planner_node(state: AgentState) -> dict:
    used = state.get("tool_calls_count", 0)
    print(f">>> [3/5] PLANNER (qwen3.5:4b) | attempt {state.get('retries', 0) + 1} | tools used: {used}...")
    sys_prompt = build_planner_prompt(
        route=state["route"],
        retrieved_notes=state.get("retrieved_notes", ""),
        verifier_errors=state.get("verifier_errors", []),
    )
    history = state["messages"][-4:]

    if used == 0:
        sys_prompt += (
            "\n\nSTRICT RULES:\n"
            "1. Follow ONLY the active route (`PLAN` or `QUIZ`).\n"
            "2. For `QUIZ`, generate ONLY 5 multiple-choice questions (options A, B, C, D) + Answer Key at the bottom. Do NOT add Fill-in-the-Blanks or Part 2."
        )
        response = llm_planner_with_tools.invoke([SystemMessage(content=sys_prompt)] + history)
    else:
        sys_prompt += (
            "\n\nIMPORTANT: Export tool already executed. "
            "Write the complete formatted English study plan or 5-question multiple-choice quiz with Answer Key now."
        )
        response = llm_planner_text.invoke([SystemMessage(content=sys_prompt)] + history)

    clean_text = _strip_think(response.content)
    print(f"    Planner draft length: {len(clean_text)} chars")
    return {"messages": [response], "draft": clean_text}


solver_tool_node = ToolNode(SOLVER_TOOLS)
planner_tool_node = ToolNode(PLANNER_TOOLS)


def collect_evidence_node(state: AgentState) -> dict:
    print(">>> [3.5/5] COLLECT EVIDENCE (Tool output captured)...")
    evidence = list(state.get("evidence", []))
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage):
            print(f"    Tool result: {msg.content}")
            evidence.append(f"[{msg.name}]: {msg.content}")
        elif isinstance(msg, HumanMessage):
            break
    return {"evidence": evidence, "tool_calls_count": state.get("tool_calls_count", 0) + 1}


def verifier_node(state: AgentState) -> dict:
    print(">>> [4/5] VERIFIER (Judge)...")
    last_user_msg = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
    payload = (
        f"TASK:\n{last_user_msg}\n\n"
        f"ROUTE: {state['route']}\n\n"
        f"EVIDENCE:\n{state.get('evidence', [])}\n\n"
        f"DRAFT:\n{state.get('draft', '')}"
    )
    res = llm_verifier.invoke([
        SystemMessage(content=build_verifier_prompt()),
        HumanMessage(content=payload),
    ])

    raw = re.sub(r"```json|```", "", res.content).strip()
    try:
        data = json.loads(raw)
        verdict = data.get("verdict", "pass").lower()
        errors = data.get("errors", [])
    except Exception:
        verdict = "pass"
        errors = []

    print(f"    Verifier verdict: {verdict}")
    retries = state.get("retries", 0)
    if verdict == "fail":
        retries += 1

    return {"verifier_verdict": verdict, "verifier_errors": errors, "retries": retries}


def escalate_node(state: AgentState) -> dict:
    print(">>> [4.5/5] ESCALATE...")
    errors_str = "\n".join(f"- {e.get('comment', str(e))}" for e in state.get("verifier_errors", []))
    trigger_alert("ESCALATION_TRIGGERED", f"Route={state['route']} failed after 2 retries. Errors: {errors_str}")
    msg = (
        "I attempted to verify this solution twice, but my quality checks flagged potential issues:\n"
        f"{errors_str}\n\n"
        "Could you double-check the problem conditions or clarify any missing constraints so we can solve it accurately?"
    )
    return {"draft": msg, "messages": [AIMessage(content=msg)]}


def _save_to_mem0_background(user_msg: str, assistant_msg: str, user_id: str):
    try:
        mem0_client.add(
            messages=[
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg},
            ],
            user_id=user_id,
            infer=False,
        )
        print("    [Background] Saved to Mem0 successfully.")
    except Exception as e:
        print(f"    [Background] Mem0 save skipped: {e}")


def finalize_node(state: AgentState) -> dict:
    print(">>> [5/5] FINALIZE (Returning answer immediately, saving memory in background)...")
    last_user_msg = next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
    final_answer = state.get("draft", "")
    user_id = state.get("user_id", "default_student")

    if state["route"] != "SMALLTALK" and last_user_msg and final_answer:
        threading.Thread(
            target=_save_to_mem0_background,
            args=(last_user_msg, final_answer, user_id),
            daemon=True,
        ).start()

    return {"messages": [AIMessage(content=final_answer)]}


def route_decision(state: AgentState) -> str:
    return "smalltalk" if state["route"] == "SMALLTALK" else "retrieve"


def after_retrieve_decision(state: AgentState) -> str:
    return "planner" if state["route"] in {"PLAN", "QUIZ"} else "solver"


def should_call_solver_tools(state: AgentState) -> str:
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None) and state.get("tool_calls_count", 0) < 1:
        return "solver_tools"
    return "verifier"


def should_call_planner_tools(state: AgentState) -> str:
    last_msg = state["messages"][-1]
    if getattr(last_msg, "tool_calls", None) and state.get("tool_calls_count", 0) < 1:
        return "planner_tools"
    return "verifier"


def after_verifier_decision(state: AgentState) -> str:
    if state["verifier_verdict"] == "pass":
        return "finalize"
    if state["retries"] < 2:
        return "planner" if state["route"] in {"PLAN", "QUIZ"} else "solver"
    return "escalate"


builder = StateGraph(AgentState)

builder.add_node("router", router_node)
builder.add_node("retrieve", retrieve_node)
builder.add_node("smalltalk", smalltalk_node)
builder.add_node("solver", solver_node)
builder.add_node("solver_tools", solver_tool_node)
builder.add_node("planner", planner_node)
builder.add_node("planner_tools", planner_tool_node)
builder.add_node("collect_evidence", collect_evidence_node)
builder.add_node("verifier", verifier_node)
builder.add_node("escalate", escalate_node)
builder.add_node("finalize", finalize_node)

builder.add_edge(START, "router")
builder.add_conditional_edges("router", route_decision, {"smalltalk": "smalltalk", "retrieve": "retrieve"})
builder.add_edge("smalltalk", "finalize")
builder.add_conditional_edges("retrieve", after_retrieve_decision, {"planner": "planner", "solver": "solver"})

builder.add_conditional_edges("solver", should_call_solver_tools, {"solver_tools": "solver_tools", "verifier": "verifier"})
builder.add_edge("solver_tools", "collect_evidence")
builder.add_edge("collect_evidence", "solver")

builder.add_conditional_edges("planner", should_call_planner_tools, {"planner_tools": "planner_tools", "verifier": "verifier"})
builder.add_edge("planner_tools", "collect_evidence")

builder.add_conditional_edges(
    "verifier",
    after_verifier_decision,
    {"finalize": "finalize", "solver": "solver", "planner": "planner", "escalate": "escalate"},
)
builder.add_edge("escalate", "finalize")
builder.add_edge("finalize", END)

app_graph = builder.compile(checkpointer=get_short_term_checkpointer())
