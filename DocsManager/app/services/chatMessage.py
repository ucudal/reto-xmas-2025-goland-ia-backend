from sqlalchemy.orm import Session
from typing import AsyncIterator

from app.models.chat_message import ChatMessage
from app.schemas.enums.sender_type import SenderType
from app.models.chat_session import ChatSession
from ag_ui.core import (
    RunAgentInput,
    RunStartedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    RunFinishedEvent,
    MessagesSnapshotEvent,
    AssistantMessage,
    TextInputContent,
    EventEncoder
)


def assistant_reply(text: str) -> str:
    return f"Respuesta del asistente a: {text}"


def create_user_message(
    db: Session,
    message: str,
    session_id=None
):
    # 1. Si no hay session_id → crear sesión nueva
    if session_id is None:
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

    # 3. Respuesta del asistente
    assistant_text = assistant_reply(message)

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
            content=assistant_msg.message
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