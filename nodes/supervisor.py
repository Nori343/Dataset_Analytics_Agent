from state.analyst_state import AnalystState


from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from config.settings import ITERATION_LIMIT, OPENAI_API_KEY, OPENAI_MODEL

class SupervisorOutput(BaseModel):
    next_node: Literal["planner", "analyst", "query_agent", "verifier", "end"] = Field(description="which node next")
    reason: str = Field(description="reason for debug")
    done: bool = Field()


def supervisor_node(state: AnalystState) -> dict:
    question = state.get("customer_message")
    iteration = state.get("iteration", 0)

    if not question:
        return {
            "next_node": "__end__",
            "supervisor_reason": "no relevant query asked",
            "done": True,
            "node_trace": ["supervisor"],
            "final_answer": "Please enter a relevant data request"
        }
    
    if not state.get("plan"):
        return {
            "next_node": "planner",
            "supervisor_reason": "no plan created yet",
            "done": False,
            "node_trace": ["supervisor"]
        }
    
    if not state.get("query_result") and not state.get("query_error") and not state.get("sql"):
             return {
                    "next_node":"query_agent",
                    "done": False,
                    "supervisor_reason": "plan but no sql route to query agent",
                    "node_trace": ["supervisor"]
                }          
           
    if state.get("query_error"):
            if iteration < ITERATION_LIMIT:
                return {
                    "next_node":"query_agent",
                    "done": False,
                    "supervisor_reason": "query agent failed try again",
                    "iteration": iteration+1,
                    "node_trace": ["supervisor"]
                }
            else:
                return {
                    "next_node": "__end__",
                    "supervisor_reason": "Iteration limit hit, query agent failed",
                    "done": True,
                    "node_trace": ["supervisor"],
                    "response": "Iteration limit hit unable to answer"
                }  
    
    if state.get("query_result") and not state.get("draft_response"):
        return {
            "next_node": "analyst",
            "supervisor_reason": "have plan and query need draft response route to analyst",
            'done': False,
            "node_trace": ["supervisor"]          
        }
    
    if state.get("draft_response") and state.get("is_verified") is None:
        return {
            "next_node": "verifier",
            "supervisor_reason": "have draft response send to verifier",
            "done": False,
            "node_trace": ["supervisor"]
        }
    
    if state.get("is_verified") == False:
        if iteration < ITERATION_LIMIT:
            return {
                    "next_node":"query_agent",
                    "done": False,
                    "supervisor_reason": "query agent output not verified try again",
                    "iteration": iteration+1,
                    "node_trace": ["supervisor"]
                }
        else:
            return{
                "next_node": "__end__",
                "supervisor_reason":"sql values not verified and iteration limit reached",
                "done": True,
                "node_trace": ["supervisor"]
            }
            
    if state.get("is_verified") is True:
        return {
            "next_node": "__end__",
            "supervisor_reason": "graph ran fully route to end",
            "response": state.get("draft_response"),
            "done": True,
            "node_trace": ["supervisor"],
        }