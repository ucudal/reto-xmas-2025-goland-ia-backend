"""Conditional routing functions for the LangGraph agent."""

from app.agents.state import AgentState


def route_after_guard_inicial(state: AgentState) -> str:
    """
    Route after Guard Inicial node validation.

    Determines the next step based on whether the prompt was flagged as malicious.

    Args:
        state: Current agent state

    Returns:
        "malicious" if the prompt is malicious, "continue" otherwise
    """
    if state.get("is_malicious", False):
        return "malicious"
    return "continue"


def route_after_guard_final(state: AgentState) -> str:
    """
    Route after Guard Final node validation.

    Determines the next step based on whether the response was flagged as risky.

    Args:
        state: Current agent state

    Returns:
        "risky" if the response is risky, "continue" otherwise
    """
    if state.get("is_risky", False):
        return "risky"
    return "continue"
