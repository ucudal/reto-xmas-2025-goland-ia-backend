"""Nodo 3: Fallback - Handles fallback processing from multiple workflow points."""

import logging

from app.agents.state import AgentState
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model="gpt-5-nano",
)

# TO DO: implementar clase nodo fallback y inicializar el llm en el init
def fallback(state: AgentState) -> AgentState:
    """
    Fallback node - Performs fallback processing.

    This node:
    1. Alerts about malicious prompt
    2. Generates an error_message from llm to show the user

    Args:
        state: Agent state containing the prompt or initial context

    Returns:
        error_message
    """

    logger.warning(
        "Defensive check triggered: Malicious prompt detected" 
    )
    
    messages = [
        SystemMessage(
            content="Your job is to generate an error message in user's language for the user explaining the database doesn't have the information to respond what the user asked"
        )
    ] + state["messages"]
    error_message = llm.invoke(messages)
    return {"messages": [error_message]}

