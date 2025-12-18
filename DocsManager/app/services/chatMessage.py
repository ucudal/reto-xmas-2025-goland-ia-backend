from sqlalchemy.orm import Session
from typing import AsyncIterator
from uuid import uuid4
import httpx
import logging

from app.models.chat_message import ChatMessage
from app.schemas.enums.sender_type import SenderType
from app.models.chat_session import ChatSession
from app.core.config import settings
from ag_ui.core import (
    RunAgentInput,
    RunStartedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    RunFinishedEvent,
    MessagesSnapshotEvent,
    AssistantMessage,
    TextInputContent
)
from ag_ui.encoder import (
    EventEncoder
)

logger = logging.getLogger(__name__)


async def call_ragmanager_agent(message: str, session_id: str = None) -> str:
    """
    Call the RAGManager service to process a message through the LangGraph agent.
    
    Args:
        message: User's message to process
        session_id: Optional session ID for conversation context
        
    Returns:
        Generated assistant response
        
    Raises:
        httpx.HTTPError: If the request to RAGManager fails
    """
    url = f"{settings.ragmanager_url}/chat/process"
    
    payload = {
        "message": message,
        "session_id": session_id
    }
    
    logger.info(f"Calling RAGManager at {url} with session_id: {session_id}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            assistant_message = data.get("message", "")
            
            logger.info("Successfully received response from RAGManager")
            return assistant_message
            
        except httpx.HTTPError as e:
            logger.error(f"Error calling RAGManager: {e}")
            raise


def create_user_message(
    db: Session,
    message: str,
    session_id=None
):
    """
    Create a user message and get response from RAGManager agent.
    
    This function:
    1. Creates or retrieves a chat session
    2. Saves the user's message to the database
    3. Calls RAGManager to process the message through the agent
    4. Saves the assistant's response to the database
    5. Returns the assistant message and session_id
    
    Args:
        db: Database session
        message: User's message text
        session_id: Optional existing session ID
        
    Returns:
        Tuple of (assistant_msg, session_id)
    """
    # 1. Si no hay session_id → crear sesión nueva
    if not session_id:
        session = ChatSession()
        db.add(session)
        db.flush()  # genera el UUID sin commit
        session_id = session.id
    else:
        session = db.get(ChatSession, session_id)
        if not session:
            raise ValueError("Chat session not found")

    # 2. Guardar mensaje del usuario
    user_msg = ChatMessage(
        session_id=session_id,
        sender=SenderType.user,
        message=message
    )
    db.add(user_msg)
    db.commit()  # Commit user message first
    
    try:
        # 3. Call RAGManager agent to process the message
        # Note: This is a sync function but we need async call
        # We'll use asyncio to run it
        import asyncio
        
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        assistant_text = loop.run_until_complete(
            call_ragmanager_agent(message, str(session_id))
        )
        
    except Exception as e:
        logger.error(f"Error getting response from RAGManager: {e}")
        # Fallback response in case of error
        assistant_text = "I'm sorry, I'm having trouble processing your request right now. Please try again later."

    # 4. Save assistant response
    assistant_msg = ChatMessage(
        session_id=session_id,
        sender=SenderType.assistant,
        message=assistant_text
    )
    db.add(assistant_msg)

    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg, session_id


async def process_agent_message(
    db: Session,
    payload: RunAgentInput
) -> AsyncIterator[str]:
    """Process agent message and generate AG-UI protocol events.
    
    Args:
        db: Database session
        payload: RunAgentInput containing the user's message and context
        
    Yields:
        AG-UI protocol events as encoded strings
    """
    encoder = EventEncoder()
    
    try:
        # Extract the user message from the messages list
        user_message_text = ""
        if payload.messages:
            last_message = payload.messages[-1]
            if hasattr(last_message, 'content'):
                if isinstance(last_message.content, list) and len(last_message.content) > 0:
                    user_message_text = last_message.content[0].text
                elif isinstance(last_message.content, str):
                    user_message_text = last_message.content
        
        # Use thread_id as session_id (AG-UI uses thread_id for conversation tracking)
        session_id = payload.thread_id if hasattr(payload, 'thread_id') else None

        if not payload.run_id:
            payload.run_id = str(uuid4())
        
        # Emit RUN_STARTED event
        run_started = RunStartedEvent(
            run_id=payload.run_id,
            thread_id=payload.thread_id
        )
        yield encoder.encode(run_started)
        
        # Process the message through the service
        assistant_msg, session_id = create_user_message(
            db=db,
            message=user_message_text,
            session_id=session_id
        )
        
        # Generate a unique message ID for the assistant response
        message_id = f"msg_{payload.run_id}"
        
        # Emit TEXT_MESSAGE_START event
        text_start = TextMessageStartEvent(
            run_id=payload.run_id,
            message_id=message_id
        )
        yield encoder.encode(text_start)
        
        # Emit TEXT_MESSAGE_CONTENT event with the assistant's response
        text_content = TextMessageContentEvent(
            run_id=payload.run_id,
            message_id=message_id,
            delta=assistant_msg.message
        )
        yield encoder.encode(text_content)
        
        # Emit TEXT_MESSAGE_END event
        text_end = TextMessageEndEvent(
            run_id=payload.run_id,
            message_id=message_id
        )
        yield encoder.encode(text_end)
        
        # Emit MESSAGES_SNAPSHOT event with the full conversation
        messages_snapshot = MessagesSnapshotEvent(
            run_id=payload.run_id,
            messages=[
                *payload.messages,  # Include previous messages
                AssistantMessage(
                    id=message_id,
                    content=[TextInputContent(text=assistant_msg.message)]
                )
            ]
        )
        yield encoder.encode(messages_snapshot)
        
        # Emit RUN_FINISHED event
        run_finished = RunFinishedEvent(
            run_id=payload.run_id
        )
        yield encoder.encode(run_finished)
        
    except Exception as e:
        # In case of error, we should emit a RUN_ERROR event
        # For now, we'll just re-raise the exception
        raise