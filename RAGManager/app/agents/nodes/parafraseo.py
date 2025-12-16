"""Nodo 4: Parafraseo - Saves message, retrieves chat history, and paraphrases user input."""

import json
import logging

from app.agents.state import AgentState
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-5-nano")


def parafraseo(state: AgentState) -> AgentState:
    """
    Parafraseo node - Saves message to DB, retrieves chat history, and paraphrases user input.

    This node:
    1. Receives a validated user message (after guard_inicial validation)
    2. Saves the user's message to the chat session in PostgreSQL (endpoint 1 - placeholder)
    3. Retrieves the last 10 messages of the conversation (endpoint 2 - placeholder)
    4. Uses the last message to understand user's intentions and the remaining 9 (older) messages as context
    5. Sends to LLM with instructions to return 3 differently phrased statements that encapsulate
       the user's intentions according to the last message and chat history

    Args:
        state: Agent state containing validated user message, chat_session_id, and user_id

    Returns:
        Updated state with chat_messages, paraphrased_text, and paraphrased_statements set
    """
    updated_state = state.copy()
    
    # Get the validated user message from state
    messages = state.get("messages", [])
    if not messages:
        logger.error("No messages found in state")
        updated_state["error_message"] = "No user message found in state"
        return updated_state
    
    # Get the last message (the validated user message)
    last_user_message = messages[-1]
    user_message_content = last_user_message.content if hasattr(last_user_message, 'content') else str(last_user_message)
    
    # TODO: Endpoint 1 - Save message to PostgreSQL database according to chat session
    # This should:
    # 1. Call an endpoint (not yet developed) that:
    #    - Saves the current user message to the chat session in PostgreSQL
    #    - Uses chat_session_id and user_id from state
    #    - Returns success/failure status
    # 2. Handle errors appropriately (session not found, permission denied, etc.)
    logger.info("Endpoint 1 (save message to DB) not yet implemented - skipping")
    
    # TODO: Endpoint 2 - Retrieve last 10 messages of the conversation
    # This should:
    # 1. Call an endpoint (not yet developed) that:
    #    - Retrieves the last 10 messages for the chat session
    #    - Returns a list of message dictionaries with structure: [{"sender": "user|assistant|system", "message": "...", "created_at": "..."}, ...]
    #    - Messages should be ordered from oldest to newest (or newest to oldest, depending on API design)
    # 2. Update state with chat_messages from the endpoint response
    # 3. Handle errors appropriately (session not found, permission denied, etc.)
    
    # Placeholder: For now, we'll simulate chat history with just the current message
    # Once the endpoint is implemented, replace this with the actual endpoint call
    chat_messages = [
        {"sender": "user", "message": user_message_content, "created_at": "2025-01-01T00:00:00"}
    ]
    updated_state["chat_messages"] = chat_messages
    logger.warning("Endpoint 2 (retrieve chat history) not yet implemented - using current message only")
    
    # Process chat history: last message (intentions) + 9 older messages (context)
    # The last message is the most recent one (for understanding intentions)
    # The remaining 9 messages are older (for context)
    if len(chat_messages) >= 10:
        # We have 10+ messages: use last one for intentions, previous 9 for context
        context_messages = chat_messages[-10:-1]  # 9 older messages
        intention_message = chat_messages[-1]  # Last message (most recent)
    elif len(chat_messages) > 1:
        # We have 2-9 messages: use last one for intentions, all previous for context
        context_messages = chat_messages[:-1]  # All older messages
        intention_message = chat_messages[-1]  # Last message
    else:
        # We have only 1 message: use it for intentions, no context
        context_messages = []
        intention_message = chat_messages[0] if chat_messages else {"sender": "user", "message": user_message_content}
    
    # Format chat history for LLM prompt
    context_text = ""
    if context_messages:
        context_lines = []
        for msg in context_messages:
            sender = msg.get("sender", "unknown")
            message = msg.get("message", "")
            context_lines.append(f"{sender.capitalize()}: {message}")
        context_text = "\n".join(context_lines)
    
    intention_text = intention_message.get("message", user_message_content)
    
    # Create LLM prompt with instructions
    system_instruction = """You are an expert at understanding user intentions and paraphrasing them in different ways.

Given a user's last message and their conversation history, your task is to return exactly 3 differently phrased statements that encapsulate the user's intentions.

The last message represents what the user wants to know or do right now. The conversation history provides context about what they've been discussing.

Requirements:
- Return exactly 3 different phrasings
- Each phrasing should capture the user's core intention from their last message
- Use the conversation history to understand context and references (like "it", "that", "the previous thing")
- Each phrasing should be a complete, standalone statement that makes sense without the full conversation
- The phrasings should be diverse - use different words, sentence structures, and perspectives
- Format your response as a JSON array of exactly 3 strings: ["statement 1", "statement 2", "statement 3"]
- Do not include any explanation, just the JSON array

Example format:
["What are the main features of the product?", "Can you explain the key characteristics of this product?", "I'd like to know what this product offers."]"""

    # Build the prompt with context and intention
    if context_text:
        user_prompt = f"""Conversation History (older messages for context):
{context_text}

Last User Message (current intention):
{intention_text}

Return 3 differently phrased statements that encapsulate the user's intention from their last message, using the conversation history for context."""
    else:
        user_prompt = f"""User Message (current intention):
{intention_text}

Return 3 differently phrased statements that encapsulate the user's intention from their message."""

    # Call LLM with the prompt
    messages_for_llm = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm.invoke(messages_for_llm)
        response_content = response.content.strip()
        
        # Parse the JSON response to extract the 3 statements
        try:
            # Try to parse as JSON array
            paraphrased_statements = json.loads(response_content)
            if isinstance(paraphrased_statements, list) and len(paraphrased_statements) >= 3:
                # Take the first 3 statements
                paraphrased_statements = paraphrased_statements[:3]
            elif isinstance(paraphrased_statements, list):
                # If less than 3, pad with the last one or use as-is
                while len(paraphrased_statements) < 3:
                    paraphrased_statements.append(paraphrased_statements[-1] if paraphrased_statements else intention_text)
            else:
                # If not a list, create a list with the response
                paraphrased_statements = [response_content, response_content, response_content]
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract statements from text
            logger.warning("LLM response is not valid JSON, attempting to parse as text")
            # Try to split by newlines or common separators
            lines = [line.strip() for line in response_content.split('\n') if line.strip()]
            if len(lines) >= 3:
                paraphrased_statements = lines[:3]
            else:
                # Fallback: use the response as-is and duplicate if needed
                paraphrased_statements = [response_content] * 3
        
        # Store the results
        updated_state["paraphrased_statements"] = paraphrased_statements
        # Store the first statement in paraphrased_text for backward compatibility
        updated_state["paraphrased_text"] = paraphrased_statements[0] if paraphrased_statements else intention_text
        
        logger.info(f"Generated {len(paraphrased_statements)} paraphrased statements")
        
    except Exception as e:
        logger.error(f"Error calling LLM for paraphrasing: {e}")
        # Fallback: use the original message
        updated_state["paraphrased_statements"] = [intention_text, intention_text, intention_text]
        updated_state["paraphrased_text"] = intention_text
        updated_state["error_message"] = f"Error in paraphrasing: {str(e)}"

    return updated_state
