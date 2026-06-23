# Run from project root: python -m eval.evals

from nodes.query_agent import query_agent_node
from nodes.analyst import analyst_node
from nodes.verifier import verifier_node
from nodes.planner import planner_node

# --- query_agent test ---
query_state = {
    "customer_message": "What was total active MRR on 2026-03-31?",
    "plan": {
        "tables": ["subscriptions"],
        "columns": ["mrr", "start_date", "end_date", "status"],
        "filters": ["active on 2026-03-31"],
        "aggregations": ["SUM(mrr)"],
        "notes": "",
    },
}

# query_out = query_agent_node(query_state)
# print("query_agent:", query_out)

# --- analyst test (stub query_result — no DB / query_agent needed) ---
analyst_state = {
    "customer_message": "What was total active MRR on 2026-03-31?",
    "sql": """
        SELECT SUM(mrr) AS total_active_mrr
        FROM subscriptions
        WHERE start_date <= '2026-03-31'
          AND (end_date IS NULL OR end_date > '2026-03-31')
          AND status = 'active'
    """.strip(),
    "query_result": [{"total_active_mrr": 1022714.76}],
}

print(planner_node({
    "customer_message": "What was total active MRR on 2026-03-31?",
    }))

# 1. Should PASS
print(verifier_node({
    "draft_response": "MRR was 1022714.76",
    "query_result": [{"x": 1022714.76}],
}))

# 2. Should FAIL
print(verifier_node({
    "draft_response": "MRR was 999999.99",
    "query_result": [{"x": 1022714.76}],
}))

# 3. Empty rows — should PASS
print(verifier_node({
    "draft_response": "No data found.",
    "query_result": [],
}))


analyst_out = analyst_node(analyst_state)
print("analyst:", analyst_out)
