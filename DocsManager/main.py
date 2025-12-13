from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

from app.api.routes.base import router as base_router
from app.api.routes.rag_test import router as rag_router

app = FastAPI()

app.include_router(base_router)
app.include_router(rag_router)


