"""
Generate synthetic RelayBoard analytics warehouse at data/relayboard.db.

Run from project root:
    python scripts/generate_db.py

All data is fictional. Seeds documented demo facts for evals (see data/README.md).
"""

from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "relayboard.db"
SCHEMA_PATH = ROOT / "data" / "schema.sql"

random.seed(42)

INDUSTRIES = [
    "Software", "Healthcare", "Finance", "Retail", "Manufacturing",
    "Education", "Media", "Logistics", "Energy", "Consulting",
]
REGIONS = ["NA", "EMEA", "APAC", "LATAM"]
SEGMENTS = ["smb", "mid_market", "enterprise"]
PLAN_TIERS = ["starter", "pro", "enterprise"]
TIER_MRR = {"starter": (99, 299), "pro": (500, 2000), "enterprise": (3000, 15000)}
METRICS = ["api_calls", "active_users", "workflow_runs"]
TICKET_CATEGORIES = ["billing", "integration", "bug", "feature_request", "onboarding"]
SEVERITIES = ["low", "medium", "high", "critical"]

# Planted account for highest ticket volume
VERTEX_DYNAMICS = {
    "company_name": "Vertex Dynamics",
    "industry": "Software",
    "region": "NA",
    "signup_date": "2022-06-15",
    "segment": "enterprise",
}

COMPANY_PREFIXES = [
    "Nova", "Apex", "Bright", "Clear", "Delta", "Echo", "Flux", "Grid",
    "Helix", "Ion", "Jade", "Kite", "Lumen", "Mosaic", "Nimbus", "Orbit",
    "Pulse", "Quanta", "Relay", "Signal", "Terra", "Unity", "Vector", "Wave",
]


def d(year: int, month: int, day: int) -> str:
    return date(year, month, day).isoformat()


def month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def add_months(dt: date, n: int) -> date:
    m = dt.month - 1 + n
    y = dt.year + m // 12
    m = m % 12 + 1
    return date(y, m, 1)


def random_company_name() -> str:
    return f"{random.choice(COMPANY_PREFIXES)} {random.choice(['Labs', 'Systems', 'Works', 'Cloud', 'Analytics'])}"


def generate_accounts(n: int = 650) -> list[dict]:
    accounts = [VERTEX_DYNAMICS.copy()]
    start = date(2022, 1, 1)
    end = date(2025, 12, 31)
    for i in range(2, n + 1):
        signup = start + timedelta(days=random.randint(0, (end - start).days))
        accounts.append({
            "account_id": i,
            "company_name": random_company_name(),
            "industry": random.choice(INDUSTRIES),
            "region": random.choice(REGIONS),
            "signup_date": signup.isoformat(),
            "segment": random.choices(SEGMENTS, weights=[50, 35, 15])[0],
        })
    accounts[0]["account_id"] = 1
    return accounts


def tier_for_segment(segment: str) -> str:
    if segment == "enterprise":
        return random.choices(PLAN_TIERS, weights=[5, 25, 70])[0]
    if segment == "mid_market":
        return random.choices(PLAN_TIERS, weights=[20, 60, 20])[0]
    return random.choices(PLAN_TIERS, weights=[70, 25, 5])[0]


def generate_subscriptions(accounts: list[dict]) -> list[dict]:
    subs: list[dict] = []
    sub_id = 1
    for acct in accounts:
        signup = date.fromisoformat(acct["signup_date"])
        tier = tier_for_segment(acct["segment"])
        lo, hi = TIER_MRR[tier]
        mrr = round(random.uniform(lo, hi), 2)
        start = signup + timedelta(days=random.randint(0, 30))
        # Most accounts stay active; some churn over time
        churn_roll = random.random()
        end_date = None
        status = "active"
        if churn_roll < 0.25:
            churn_month = random.randint(0, 35)
            churn_dt = add_months(start, churn_month)
            if churn_dt <= date(2026, 3, 31):
                end_date = churn_dt.isoformat()
                status = "churned"
        subs.append({
            "subscription_id": sub_id,
            "account_id": acct["account_id"],
            "plan_tier": tier,
            "mrr": mrr,
            "start_date": start.isoformat(),
            "end_date": end_date,
            "status": status if end_date else "active",
        })
        sub_id += 1

    # --- Planted fact 1: Enterprise churn spike in March 2025 ---
    enterprise_subs = [s for s in subs if s["plan_tier"] == "enterprise" and s["status"] == "active"]
    for s in random.sample(enterprise_subs, min(18, len(enterprise_subs))):
        s["end_date"] = d(2025, 3, random.randint(1, 28))
        s["status"] = "churned"

    # --- Planted fact 2: Pro tier highest MRR share on 2026-03-31 ---
    # Boost pro subs substantially; downgrade active enterprise MRR so pro leads
    for s in subs:
        if s["status"] == "active" and s["plan_tier"] == "pro":
            s["mrr"] = round(s["mrr"] * 2.2, 2)
        if s["status"] == "active" and s["plan_tier"] == "enterprise":
            s["mrr"] = round(s["mrr"] * 0.55, 2)
        if s["status"] == "active" and s["plan_tier"] == "starter":
            s["mrr"] = round(s["mrr"] * 0.9, 2)

    return subs


def generate_usage_daily(accounts: list[dict]) -> list[dict]:
    rows: list[dict] = []
    uid = 1
    history_start = date(2024, 1, 1)
    history_end = date(2026, 3, 31)
    q1_2024_ids = {
        a["account_id"]
        for a in accounts
        if date.fromisoformat(a["signup_date"]) <= date(2024, 3, 31)
        and date.fromisoformat(a["signup_date"]) >= date(2024, 1, 1)
    }
    current = history_start
    while current <= history_end:
        for acct in accounts:
            if date.fromisoformat(acct["signup_date"]) > current:
                continue
            base = {"api_calls": 5000, "active_users": 50, "workflow_runs": 200}[METRICS[0]]
            for metric in METRICS:
                mult = {"api_calls": 1.0, "active_users": 0.01, "workflow_runs": 0.04}[metric]
                value = base * mult * random.uniform(0.7, 1.3)
                # Planted fact 5: Q1 2024 cohort usage drop in late 2025
                if acct["account_id"] in q1_2024_ids and current >= date(2025, 10, 1):
                    value *= 0.55
                rows.append({
                    "usage_id": uid,
                    "account_id": acct["account_id"],
                    "usage_date": current.isoformat(),
                    "metric": metric,
                    "value": round(value, 2),
                })
                uid += 1
        current += timedelta(days=7)  # weekly samples to keep row count manageable
    return rows


def generate_support_tickets(accounts: list[dict]) -> list[dict]:
    rows: list[dict] = []
    tid = 1
    for acct in accounts:
        n_tickets = random.randint(0, 8)
        if acct["company_name"] == "Vertex Dynamics":
            n_tickets = 85  # Planted fact 4: highest volume
        for _ in range(n_tickets):
            created = date(2024, 1, 1) + timedelta(days=random.randint(0, 820))
            severity = random.choice(SEVERITIES)
            resolution = round(random.uniform(1, 72), 1)
            # Planted fact 3: APAC underperforms on SLA
            sla_met = 1 if random.random() < 0.82 else 0
            if acct["region"] == "APAC":
                sla_met = 1 if random.random() < 0.58 else 0
            rows.append({
                "ticket_id": tid,
                "account_id": acct["account_id"],
                "created_at": created.isoformat(),
                "category": random.choice(TICKET_CATEGORIES),
                "severity": severity,
                "resolution_hours": resolution,
                "sla_met": sla_met,
            })
            tid += 1
    return rows


def generate_plan_changes(accounts: list[dict], subscriptions: list[dict]) -> list[dict]:
    rows: list[dict] = []
    cid = 1
    tier_order = {"starter": 0, "pro": 1, "enterprise": 2}
    for acct in random.sample(accounts, min(120, len(accounts))):
        sub = next(s for s in subscriptions if s["account_id"] == acct["account_id"])
        from_tier = sub["plan_tier"]
        if from_tier == "starter":
            to_tier = random.choice(["pro", "enterprise"])
        elif from_tier == "pro":
            to_tier = random.choice(["starter", "enterprise"])
        else:
            to_tier = random.choice(["pro", "starter"])
        delta = (tier_order[to_tier] - tier_order[from_tier]) * random.uniform(200, 800)
        change_dt = date.fromisoformat(acct["signup_date"]) + timedelta(days=random.randint(60, 400))
        rows.append({
            "change_id": cid,
            "account_id": acct["account_id"],
            "change_date": change_dt.isoformat(),
            "from_tier": from_tier,
            "to_tier": to_tier,
            "mrr_delta": round(delta, 2),
        })
        cid += 1
    return rows


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    accounts = generate_accounts(650)
    subscriptions = generate_subscriptions(accounts)
    usage = generate_usage_daily(accounts)
    tickets = generate_support_tickets(accounts)
    plan_changes = generate_plan_changes(accounts, subscriptions)

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())
    conn.executemany(
        "INSERT INTO accounts VALUES (:account_id, :company_name, :industry, :region, :signup_date, :segment)",
        accounts,
    )
    conn.executemany(
        "INSERT INTO subscriptions VALUES (:subscription_id, :account_id, :plan_tier, :mrr, "
        ":start_date, :end_date, :status)",
        subscriptions,
    )
    conn.executemany(
        "INSERT INTO usage_daily VALUES (:usage_id, :account_id, :usage_date, :metric, :value)",
        usage,
    )
    conn.executemany(
        "INSERT INTO support_tickets VALUES (:ticket_id, :account_id, :created_at, :category, "
        ":severity, :resolution_hours, :sla_met)",
        tickets,
    )
    conn.executemany(
        "INSERT INTO plan_changes VALUES (:change_id, :account_id, :change_date, :from_tier, :to_tier, :mrr_delta)",
        plan_changes,
    )
    conn.commit()
    conn.close()
    print(f"Created {DB_PATH} with {len(accounts)} accounts, {len(subscriptions)} subscriptions.")


if __name__ == "__main__":
    main()
