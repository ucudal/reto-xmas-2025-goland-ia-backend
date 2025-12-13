import logging
from fastapi import FastAPI

from app.api.routes import admin, base
from app.core.database_connection import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Docs Manager API", version="0.1.0")

# Include routers
app.include_router(base.router)
app.include_router(admin.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup."""
    try:
        init_db()
        logging.info("Database initialized successfully")

        # Initialize RabbitMQ connection (will be used when publishing messages)
        from app.core.rabbitmq import rabbitmq
        logging.info("RabbitMQ module loaded")
    except Exception as e:
        logging.error(f"Failed to initialize services: {e}")
        raise


