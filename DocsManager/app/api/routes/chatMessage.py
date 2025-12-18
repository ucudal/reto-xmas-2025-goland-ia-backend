from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db_connection import get_db
from ag_ui.core import RunAgentInput
from app.services.chatMessage import process_agent_message


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
    return StreamingResponse(
        process_agent_message(db, payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx if present
        }
    )
