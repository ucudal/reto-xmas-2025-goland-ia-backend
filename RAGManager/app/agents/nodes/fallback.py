"""Nodo 3: Fallback - Fallback processing for malicious prompts and risky content."""

import logging

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    """Lazy initialization of LLM instance."""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="gpt-5-nano",
        )
    return _llm


def fallback(state: AgentState) -> dict:
    """
    Fallback node - Performs fallback processing.

    This node:
    1. Alerts about malicious prompt or PII detection
    2. Generates an error message from llm to show the user

    Args:
        state: Agent state containing the prompt or initial context

    Returns:
        dict: A dictionary with a "messages" key containing a list with the generated error message from the LLM.
    """

    # Check for PII/Risky content (from guard_final)
    if state.get("is_risky"):
        logger.warning(
            "Defensive check triggered: PII/Risky content detected in response"
        )
        system_message_content = (
            "Your job is to generate an error message in user's language explaining "
            "that the response cannot be provided because it contains sensitive or private information."
        )

    # Check for Malicious prompt (from guard_inicial)
    elif state.get("is_malicious"):
        logger.warning(
            "Defensive check triggered: Malicious prompt detected"
        )
        system_message_content = (
            "Your job is to generate an error message in user's language for the user "
            "explaining the database doesn't have the information to answer the user's question"
        )

    # Generic Fallback (neither risky nor malicious)
    else:
        logger.info(
            "Fallback triggered: Generic fallback (no risky/malicious flag)"
        )
        system_message_content = (
            "Your job is to generate an error message in user's language for the user "
            "explaining the database doesn't have the information to answer the user's question"
        )

    messages = [
        SystemMessage(content=system_message_content)
    ] + state["messages"]

    error_message = _get_llm().invoke(messages)
    return {"messages": [error_message]}

