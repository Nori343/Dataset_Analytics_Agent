from __future__ import annotations

import re
from typing import Any
from state.analyst_state import AnalystState

FLOAT_TOLERANCE = 0.015  # 1.5% relative or absolute for small numbers

_MONTH_YEAR = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{4}\b",
    re.IGNORECASE,
)

_MONTH_DAY_YEAR = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)


def _text_for_metric_numbers(text: str) -> str:
    """Remove date literals so verifier/evals don't treat years/ISO dates as metrics."""
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text)
    text = _MONTH_DAY_YEAR.sub(" ", text)
    text = _MONTH_YEAR.sub(" ", text)
    return text


def _extract_numbers(text: str) -> list[float]:
    """Pull numeric literals from answer text (integers and decimals)."""
    text = _text_for_metric_numbers(text)
    # Prefer comma-grouped and decimal forms before plain integers
    pattern = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+"
    found = []
    for match in re.finditer(pattern, text):
        raw = match.group().replace(",", "")
        try:
            found.append(float(raw))
        except ValueError:
            continue
    return found


def _flatten_values(rows: list[dict[str, Any]]) -> list[float]:
    "Pull values from list of dicts rows"
    nums: list[float] = []
    for row in rows:
        for v in row.values():
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                nums.append(float(v))
            elif isinstance(v, str) and re.match(r"^-?\d+(\.\d+)?$", v.strip()):
                nums.append(float(v.strip()))
    return nums


def _number_in_results(num: float, result_nums: list[float]) -> bool:
    "check if num in result_nums"
    for rv in result_nums:
        if abs(num - rv) <= max(0.01, abs(rv) * FLOAT_TOLERANCE):
            return True
        # Also match rounded display forms (e.g. 1234.56 → 1,234.56 won't match comma form
        # but integer rounding should)
        if abs(round(num) - round(rv)) <= 1 and abs(rv) > 100:
            return True
    return False


def verifier_node(state: AnalystState) -> dict:
    rows = state.get("query_result")
    draft = state.get("draft_response")
    error = state.get("query_error")

    if error:
        return {
            "is_verified": False,
            "verification_notes": "sql error not able to verify",
            "node_trace": ["verifier"]
        }
    
    if rows is None:
        return {
            "is_verified": False,
            "verification_notes": "No query result cannot verify",
            "node_trace": ["verifier"]
        }

    if not (draft or "").strip():
        return {
            "is_verified": False,
            "verification_notes": "empty draft_response cannot verify",
            "node_trace": ["verifier"]
        }
    
    draft_nums = _extract_numbers(draft)
    row_nums = _flatten_values(rows)
   
    if not rows:
        acknowledges = any(w in draft.lower() for w in ("no ", "none", "zero rows", "empty", "no data"))
        has_metric_numbers = bool(draft_nums)  # already computed above
        ok = acknowledges and not has_metric_numbers      
        if ok:
            return {
            "is_verified": True,
            "verification_notes": "query_result empty and no numbers in draft_response",
            "final_response": draft,
            "node_trace": ["verifier"]
        }
        else:
            return {
                "is_verified": False,
                "verification_notes": "query_result empty, either has num in draft_response or doesn't ackowledge emptiness",
                "node_trace": ["verifier"]               
            }
               
    for num in draft_nums:
        if not _number_in_results(num, row_nums):
            return {
                 "is_verified": False,
                "verification_notes": "Failed verification number not in query_result",
                "node_trace": ["verifier"]
        }



    return {
        "is_verified": True,
        "verification_notes": "all numbers grounded",
        "response": draft,
        "node_trace": ["verifier"]
        }
    