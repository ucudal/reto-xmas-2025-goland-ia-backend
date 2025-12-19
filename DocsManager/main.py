import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, base
from app.core.db_connection import init_db
# Import models to ensure SQLAlchemy can resolve relationships
from app.models import Document, DocumentChunk  # noqa: F401

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Docs Manager API", version="0.1.0")

# Configure CORS - Allow any localhost or 127.0.0.1 with any port
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],  # Includes OPTIONS
    allow_headers=["*"],
)

# Include routers
app.include_router(base.router)
app.include_router(admin.router)

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup."""
    try:
        init_db()
        logging.info("Database initialized successfully")

        # Initialize RabbitMQ connection, exchange and queue
        from app.core.rabbitmq import rabbitmq
        from app.core.config import settings
        rabbitmq.connect()
        rabbitmq.declare_exchange(settings.rabbitmq_exchange_name)
        rabbitmq.declare_queue(settings.rabbitmq_queue_name, settings.rabbitmq_exchange_name)
        logging.info(f"RabbitMQ initialized: exchange='{settings.rabbitmq_exchange_name}', queue='{settings.rabbitmq_queue_name}'")
    except Exception as e:
        logging.error(f"Failed to initialize services: {e}")
        raise

