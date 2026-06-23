from openai import OpenAI
from state.analyst_state import AnalystState
from pydantic import BaseModel, Field
from langchain.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from config.settings import OPENAI_API_KEY, OPENAI_MODEL
from tools.sql_tools import run_readonly_sql
from nodes.prompts import SCHEMA_SUMMARY, QUERY_AGENT
import json


class SQLDraft(BaseModel):
    sql: str = Field(description="sql str converted from planner output")

def build_human_prompt(state: AnalystState):
    plan = state.get("plan")
    return json.dumps(plan, indent=2)


def query_agent_node(state: AnalystState) -> dict:
    if not OPENAI_API_KEY:
        sql = """
        SELECT ROUND(SUM(mrr), 2) AS active_mrr
        FROM subscriptions
        WHERE start_date <= '2026-03-31'
          AND (end_date IS NULL OR end_date > '2026-03-31')
          AND status = 'active'
        """.strip()
    else:
        llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY)
        structured = llm.with_structured_output(SQLDraft)
        draft = structured.invoke([
        SystemMessage(content=QUERY_AGENT),
        HumanMessage(content=f"query: {state.get("customer_message")} \n\n PlannerOutput: {build_human_prompt(state)}")])
        sql = draft.sql.strip()

    data = run_readonly_sql(sql)

    if "error" in data:
        return {
                "query_error": data.get("error"),
                "query_result": None,
                "node_trace": ["query_agent"]
            }
        
    return {
            "query_result": data.get("rows"),
            "query_error": None,
            "sql": sql,
            "node_trace": ["query_agent"]
        }