from state.analyst_state import AnalystState
from langchain_openai import ChatOpenAI
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from config.settings import OPENAI_MODEL, OPENAI_API_KEY
from pydantic import BaseModel, Field
from nodes.prompts import ANLAYST


class AnalystOutput(BaseModel):
    draft_response: str = Field(description="draft of user facing response")

def analyst_node(state: AnalystState) -> dict:
    rows = state.get("query_result") or []
    if not OPENAI_API_KEY:
        if rows:
            nums = []
            for row in rows:
                for v in row.values():
                    if isinstance(v, (int, float)):
                        nums.append(f"{v:.2f}" if isinstance(v, float) else str(v))
            draft = f"Results: {', '.join(nums[:6])}."
        else:
            draft = "Unable to generate answer without query results or API key."
    else:
        query = state.get("customer_message")
        sql_result = state.get("query_result")
        sql = state.get("sql")

        llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)
        structured = llm.with_structured_output(AnalystOutput)
        out: AnalystOutput = structured.invoke([
            SystemMessage(ANLAYST),
            HumanMessage(f"Query: {query} \n\n sql: {sql} \n\n sql_result: {sql_result}")
        ])
        draft = out.draft_response

    return {
        "draft_response": draft,
        "messages": [AIMessage(content=draft)],
        "node_trace": ["analyst"]
    }