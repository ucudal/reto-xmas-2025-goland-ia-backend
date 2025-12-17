import logging
import threading

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from app.api.routes import documents
from app.core.database_connection import init_db
from app.workers.pdf_processor_consumer import start_consumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="RAG Manager API", version="0.1.0")

# Include routers
app.include_router(documents.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database and start RabbitMQ consumer on startup."""
    try:
        init_db()
        logging.info("Database initialized successfully")
        
        # Start RabbitMQ consumer in a separate daemon thread
        consumer_thread = threading.Thread(target=start_consumer, daemon=True)
        consumer_thread.start()
        logging.info("RabbitMQ consumer started successfully")
        
    except Exception as e:
        logging.error(f"Failed to initialize: {e}")
        raise


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
def health_check():
    return {"message": "200 corriendo..."}


