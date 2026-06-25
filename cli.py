"""CLI entry point for RelayBoard Dataset Analyst."""

from __future__ import annotations

import argparse
import json
import sys
import uuid

from graph.builder import run_question


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Dataset Analytics CLI")
    sub = parser.add_subparsers(dest="command")

    ask_p = sub.add_parser("ask", help="Ask an analytics question")
    ask_p.add_argument("question", nargs="+", help="Analytics question")
    ask_p.add_argument("--thread-id", dest="thread_id", default=None, help="Thread ID for this run")
    ask_p.add_argument("--debug", action="store_true", help="Print SQL, results, and trace")

    demo = sub.add_parser("demo", help="Run three sample questions")

    args = parser.parse_args(argv)

    if args.command == "ask":
        question = " ".join(args.question)
        tid = args.thread_id or str(uuid.uuid4())
        result = run_question(question=question, thread_id=tid)

        print(result.get("response") or result.get("draft_response") or "No response made graph failed")
        if args.debug:
            debug = {
                "thread_id": tid,
                "node_trace": result.get("node_trace"),
                "sql": result.get("sql"),
                "query_result": result.get("query_result"),
                "query_error": result.get("query_error"),
                "is_verified": result.get("is_verified"),
                "verification_notes": result.get("verification_notes"),
                "supervisor_reason": result.get("supervisor_reason"),
                "plan": result.get("plan"),
            }
            print("\n--- debug ---")
            print(json.dumps(debug, indent=2, default=str))

        return 0
    
    if args.command == "demo":
        samples = [
            "What was total active MRR on 2026-03-31?",
            "How many subscriptions churned in March 2025?",
            "Which account has the most support tickets?",
        ]
        for q in samples:
            tid = str(uuid.uuid4())
            print(f"\nQ: {q}")
            result = run_question(question=q, thread_id=tid)
            print(f"A: {result.get('response') or result.get('draft_response') or 'N/A'}")
        return 0

    parser.print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main())