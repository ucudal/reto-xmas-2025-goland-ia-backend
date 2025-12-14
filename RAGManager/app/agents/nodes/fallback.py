"""Nodo 3: Fallback Inicial - Initial fallback processing."""

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
    1. Alerts about malicious prompt or PII detection
    2. Generates an error_message from llm to show the user

    Args:
        state: Agent state containing the prompt or initial context

    Returns:
        error_message
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
        
    # Check for Malicious prompt (from guard_inicial) - Default fallback
    else:
        # Assuming is_malicious is True if we are here and not is_risky, or just a general fallback
        logger.warning(
            "Defensive check triggered: Malicious prompt detected" 
        )
        system_message_content = (
            "Your job is to generate an error message in user's language for the user "
            "explaining the database doesn't have the information to respond what the user asked"
        )
    
    messages = [
        SystemMessage(content=system_message_content)
    ] + state["messages"]
    
    error_message = llm.invoke(messages)
    return {"messages": [error_message]}

