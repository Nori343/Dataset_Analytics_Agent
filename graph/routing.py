"""Conditional routing from supervisor to worker nodes."""

from __future__ import annotations

from state.analyst_state import AnalystState, NodeName


def route_after_supervisor(state: AnalystState) -> NodeName:
    """Read supervisor's next_node and return the next graph node (or END)."""
    nxt = state.get("next_node") or "__end__"
    if nxt == "__end__":
        return "__end__"
    return nxt
