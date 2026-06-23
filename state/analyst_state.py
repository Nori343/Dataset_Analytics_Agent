from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class Plan(TypedDict, total=False):
    tables: list[str] | None
    columns: list[str] | None
    filters: list[str] | None
    aggregations: list[str] | None
    notes: str | None

NodeName = Literal["supervisor", "planner", "query_agent", "analyst", "verifier", "__end__"]

class AnalystState(TypedDict, total=False):

    customer_message: str
    thread_id: str

    supervisor_reason: str | None
    next_node: str | None
    plan: Plan | None
    sql: str | None
    query_result: list[dict[str, any]] | None
    query_error: str | None
    is_verified: bool | None
    verfication_notes: str | None
    draft_response: str | None
    response: str | None
    iteration: int | None

    node_trace: Annotated[list[str], operator.add]
