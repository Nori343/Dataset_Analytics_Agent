from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import max_retries

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "relayboard.db"
SCHEMA_PATH = DATA_DIR / "schema.sql"


SQL_QUERY_TIMEOUT_SECONDS = 5.0
ALLOWED_TABLES = frozenset({
    "accounts", "subscriptions", "usage_daily", "support_tickets", "plan_changes",
})



OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PROJECT_ROOT = Path(__file__).resolve().parent.parent

ITERATION_LIMIT = 3