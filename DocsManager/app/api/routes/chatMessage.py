from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import AsyncIterator

from app.core.db_connection import get_db
from ag_ui.core import (
    RunAgentInput,
    RunStartedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    RunFinishedEvent,
    MessagesSnapshotEvent,
    UserMessage,
    AssistantMessage,
    TextInputContent,
    EventEncoder
)
from app.services.chatMessage import create_user_message


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post(
    "/messages",
)
async def post_user_message(
    payload: RunAgentInput,
    db: Session = Depends(get_db)
):
    """Handle chat messages using the AG-UI protocol.
    
    This endpoint accepts RunAgentInput and returns a stream of AG-UI events.
    """
    async def event_generator() -> AsyncIterator[str]:
        """Generate AG-UI protocol events."""
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
    
    return StreamingResponse(
        event_generator(),
    )
