import logging
from fastapi import FastAPI

from app.api.routes import admin, base
from app.api.routes.chatMessage import router as chat_router
from app.core.db_connection import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Docs Manager API", version="0.1.0")

# Include routers
app.include_router(base.router)
app.include_router(admin.router)
app.include_router(chat_router)

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

