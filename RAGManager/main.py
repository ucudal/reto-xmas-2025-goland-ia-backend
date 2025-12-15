import logging
from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from app.api.routes import chat, documents
from app.core.database_connection import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="RAG Manager API", version="0.1.0")

# Include routers
app.include_router(chat.router)
app.include_router(documents.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        init_db()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")
        raise


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
def health_check():
    return {"message": "200 corriendo..."}


