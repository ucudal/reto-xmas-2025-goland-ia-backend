"""Nodo 4: Parafraseo - Paraphrases user input."""

from app.agents.state import AgentState
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-5-nano")


def parafraseo(state: AgentState) -> AgentState:
    """
    Parafraseo node - Paraphrases the user input.

    This node:
    1. Takes the adjusted text from Fallback Inicial
    2. Paraphrases it to improve clarity or adjust format
    3. Prepares text for retrieval step

    Args:
        state: Agent state containing adjusted_text

    Returns:
        Updated state with paraphrased_text set
    """
    # TODO: Implement paraphrasing logic
    # This should:
    # 1. Use an LLM or paraphrasing model to rephrase the text
    # 2. Improve clarity, adjust tone, or format as needed
    # 3. Set paraphrased_text with the result

    # Paraphrase the last message using history
    
    system_instruction = """You are an expert at paraphrasing user questions to be standalone and clear, given the conversation history.
Reformulate the last user message to be a self-contained query that includes necessary context from previous messages.
Do not answer the question, just rewrite it."""

    messages = [SystemMessage(content=system_instruction)] + state["messages"]
    
    response = llm.invoke(messages)
    updated_state = state.copy()  # Create a copy of the state to update
    updated_state["paraphrased_text"] = response.content

    return updated_state
