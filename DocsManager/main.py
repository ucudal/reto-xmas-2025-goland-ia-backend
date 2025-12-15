from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

from app.api.routes.base import router as base_router
from app.api.routes.chatMessage import router as chat_router

app = FastAPI()

app.include_router(base_router)

app.include_router(chat_router)

