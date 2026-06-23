from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from graph.routing import route_after_supervisor
from nodes.analyst import analyst_node
from nodes.planner import planner_node
from nodes.query_agent import query_agent_node
from nodes.supervisor import supervisor_node
from nodes.verifier import verifier_node
from state.analyst_state import AnalystState
from langchain.messages import HumanMessage


def build_graph(*, with_checkpointer: bool = True):
    """Build supervisor-hub graph over shared AnalystState."""
    graph = StateGraph(AnalystState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("planner", planner_node)
    graph.add_node("query_agent", query_agent_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("verifier", verifier_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "planner": "planner",
            "query_agent": "query_agent",
            "analyst": "analyst",
            "verifier": "verifier",
            "__end__": END,
        },
    )

    for worker in ("planner", "query_agent", "analyst", "verifier"):
        graph.add_edge(worker, "supervisor")

    checkpointer = MemorySaver() if with_checkpointer else None
    return graph.compile(checkpointer=checkpointer)

def run_question(*, question:str, thread_id: str, graph = None):
    app = graph or build_graph(with_checkpointer=True)
    config = {"configurable": {"thread_id": thread_id}}
    initial: AnalystState = {
        "customer_message": question,
        "thread_id": thread_id,
        "messages": [HumanMessage(content=question)],
        "next_node": None,
        "plan": None,
        "sql": None,
        "query_result": None,
        "query_error": None,
        "is_verified": None,
        "draft_response": None,
        "response": None
    }
    final = app.invoke(initial, config=config)
    return final