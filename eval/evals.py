# Run from project root: pytest eval/evals.py

from __future__ import annotations

import os

import pytest

from graph.builder import run_question
from nodes.analyst import analyst_node
from nodes.planner import planner_node
from nodes.query_agent import query_agent_node
from nodes.verifier import verifier_node
from tools.sql_tools import run_readonly_sql

requires_llm = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="needs OPENAI_API_KEY",
)

MRR_PLAN = {
    "tables": ["subscriptions"],
    "columns": ["mrr", "start_date", "end_date", "status"],
    "filters": ["active subscriptions on 2026-03-31"],
    "aggregations": ["SUM(mrr)"],
    "notes": "offline eval fixture",
}


CHURN_SQL = """
SELECT COUNT(*) AS churn_count
FROM subscriptions
WHERE end_date >= '2025-03-01' AND end_date < '2025-04-01'
""".strip()


def _assert_verified_graph(out, *, answer_contains: str) -> None:
    """Shared checks for full-graph golden evals."""
    assert out.get("response"), out
    assert out.get("is_verified") is True, out
    answer = (out.get("response") or "").replace(",", "")
    assert answer_contains in answer, out
    trace = out.get("node_trace") or []
    for node in ("planner", "query_agent", "analyst", "verifier"):
        assert node in trace, out


def test_sql_churn_march_2025():
    out = run_readonly_sql(CHURN_SQL)
    assert "error" not in out, out
    assert out["rows"][0]["churn_count"] == 20, out


def test_sql_reject_insert():
    out = run_readonly_sql(
        "INSERT INTO accounts VALUES (9999, 'Bad', 'X', 'NA', '2024-01-01', 'smb')"
    )
    assert "error" in out, out
    assert "Only SELECT" in out["error"], out


def test_sql_reject_disallowed_table():
    out = run_readonly_sql("SELECT * FROM secret_users")
    assert "error" in out, out
    assert "allowlist" in out["error"].lower(), out


def test_verifier_pass():
    out = verifier_node({
        "draft_response": "MRR was 1022714.76",
        "query_result": [{"x": 1022714.76}],
    })
    assert out["is_verified"] is True, out


def test_verifier_fail_hallucinated():
    out = verifier_node({
        "draft_response": "Active MRR is 999999.99 which is very high.",
        "query_result": [{"active_mrr": 123456.78}],
    })
    assert out["is_verified"] is False, out


def test_analyst_offline_mrr(monkeypatch):
    monkeypatch.setattr("nodes.analyst.OPENAI_API_KEY", "")
    query = query_agent_node({
        "customer_message": "What was total active MRR on 2026-03-31?",
        "plan": MRR_PLAN,
    })
    out = analyst_node({
        "customer_message": "What was total active MRR on 2026-03-31?",
        "plan": MRR_PLAN,
        "sql": query["sql"],
        "query_result": query["query_result"],
        "query_error": query["query_error"],
    })
    assert "1022714.76" in out["draft_response"], out


@requires_llm
def test_planner_mrr_mentions_subscriptions():
    out = planner_node({"customer_message": "What was total active MRR on 2026-03-31?"})
    tables = [t.lower() for t in out["plan"]["tables"]]
    assert "subscriptions" in tables, out


@requires_llm
def test_analyst_mrr_mentions_subscriptions():
    plan = planner_node({"customer_message": "What was total active MRR on 2026-03-31?"})
    query = query_agent_node({
        "customer_message": "What was total active MRR on 2026-03-31?",
        "plan": plan["plan"],
    })
    out = analyst_node({
        "customer_message": "What was total active MRR on 2026-03-31?",
        "plan": plan["plan"],
        "sql": query["sql"],
        "query_result": query["query_result"],
        "query_error": query["query_error"],
    })
    draft = out["draft_response"]
    assert draft, out
    # Analyst should cite the SQL result, not invent numbers
    verifier_out = verifier_node({
        "draft_response": draft,
        "query_result": query["query_result"],
    })
    assert verifier_out["is_verified"] is True, verifier_out


@requires_llm
def test_e2e_active_mrr():
    out = run_question(
        question="What was total active MRR on 2026-03-31?",
        thread_id="test-e2e-active-mrr",
    )
    _assert_verified_graph(out, answer_contains="1022714.76")


@requires_llm
def test_e2e_churn_march_2025():
    out = run_question(
        question="How many subscriptions churned in March 2025?",
        thread_id="test-e2e-churn-march-2025",
    )
    _assert_verified_graph(out, answer_contains="20")


@requires_llm
def test_e2e_lowest_sla():
    out = run_question(
        question="Which region has the lowest support SLA met rate?",
        thread_id="test-e2e-lowest-sla",
    )
    answer = out.get("response") or ""
    assert answer, out
    assert "APAC" in answer, out


@requires_llm
def test_e2e_plan_tier_highest_mrr():
    out = run_question(
        question="Which plan tier had the highest active MRR on 2026-03-31?",
        thread_id="test-e2e-plan-tier-mrr",
    )
    answer = out.get("response") or ""
    assert answer, out
    assert "pro" in answer.lower(), out


def test_e2e_empty():
    out = run_question(
        question="",
        thread_id="test-e2e-empty",
    )
    assert out["response"] == "Please enter a relevant data request", out

@requires_llm
def test_e2e_gibberish():
    out = run_question(question="asdfgh qwerty", thread_id="test-gibberish")
    print("\n--- gibberish output ---")
    print("response:", out.get("response"))
    print("draft_response:", out.get("draft_response"))
    print("plan:", out.get("plan"))
    print("supervisor_reason:", out.get("supervisor_reason"))
    print("is_verified:", out.get("is_verified"))
    print("query_error:", out.get("query_error"))
    print("sql:", out.get("sql"))
    print("node_trace:", out.get("node_trace"))
    print("--- end gibberish ---\n")
    assert "analytics" in (out.get("response") or "").lower(), out
    assert out.get("supervisor_reason") == "plan has no tables — question not actionable", out
    trace = out.get("node_trace") or []
    assert "query_agent" not in trace, out