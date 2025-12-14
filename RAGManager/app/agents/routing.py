"""Conditional routing functions for the LangGraph agent."""

from app.agents.state import AgentState


def route_after_guard(state: AgentState) -> str:
    """
    Route after Guard Inicial node (Nodo 2) validation.

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
    Route after Guard Final node validation (PII detection in generated response).

    Determines the next step based on whether the generated response was flagged as risky (PII detected).

    Args:
        state: Current agent state

    Returns:
        "risky" if the response contains PII, "continue" otherwise
    """
    if state.get("is_risky", False):
        return "risky"
    return "continue"
