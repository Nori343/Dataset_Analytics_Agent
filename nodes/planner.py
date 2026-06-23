from __future__ import annotations
from config.settings import OPENAI_API_KEY, OPENAI_MODEL

from langchain_openai import ChatOpenAI
from state.analyst_state import Plan, AnalystState
from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from nodes.prompts import PLANNER

class PlanOutput(BaseModel):
    tables: list[str] = Field(description="Tables to query")
    columns: list[str] = Field(description="Relevant columns")
    filters: list[str] = Field(description="WHERE conditions in plain English")
    aggregations: list[str] = Field(description="GROUP BY / aggregates needed")
    notes: str = Field(default="", description="Multi-step or join notes")

def planner_node(state: AnalystState) -> dict:
    query = state.get("customer_message")
    llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY)
    structured = llm.with_structured_output(PlanOutput)
    planout = structured.invoke([
        SystemMessage(PLANNER),
        HumanMessage(f"query: {query}")
    ])
    plan = {
        "tables": planout.tables,
        "columns": planout.columns,
        "filters": planout.filters,
        "aggregations": planout.aggregations,
        "notes": planout.notes
    }
    return {
        "plan": plan,
        "node_trace": ["planner"]
    }