import logging
from fastapi import FastAPI

from app.api.routes import router as api_router
from app.api.routes.base import router as base_router
from app.core.database_connection import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="RAG Manager API", version="0.1.0")

# Global (non-versioned) routes
app.include_router(base_router)

# Versioned API routes
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        init_db()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")
        raise