import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.chatMessage import router as chat_router
from app.api.routes import router as api_router
from app.api.routes.base import router as base_router
from app.core.database_connection import init_db
from app.workers.pdf_processor_consumer import start_consumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="RAG Manager API", version="0.1.0")

# Configure CORS - Allow any localhost or 127.0.0.1 with any port
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],  # Includes OPTIONS
    allow_headers=["*"],
)

# Global (non-versioned) routes
app.include_router(base_router)

# Versioned API routes
app.include_router(api_router)

# Virtual Assistant routes
app.include_router(chat_router)

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


