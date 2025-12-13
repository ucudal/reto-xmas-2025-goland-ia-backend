import logging
from fastapi import FastAPI

from app.api.routes import admin
from app.core.database_connection import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Docs Manager API", version="0.1.0")

# Include routers
app.include_router(admin.router)


@app.on_event("startup")
async def startup_event():
    """
    Initialize application resources during startup.
    
    Initializes the database and imports the RabbitMQ module so it is available for later use. If any step fails, the original exception is re-raised to abort application startup.
    
    Raises:
        Exception: If database initialization or module import fails.
    """
    try:
        init_db()
        logging.info("Database initialized successfully")

        # Initialize RabbitMQ connection (will be used when publishing messages)
        from app.core.rabbitmq import rabbitmq
        logging.info("RabbitMQ module loaded")
    except Exception as e:
        logging.error(f"Failed to initialize services: {e}")
        raise


@app.get("/")
async def root():
    """
    Return a simple JSON object identifying the API and its version.
    
    Returns:
        dict: A dictionary with a 'message' key containing the API name and version string.
    """
    return {"message": "Docs Manager API - FastApi 1"}

app.include_router(base_router)

@app.get("/health")
def health_check():
    """
    Return a simple health status message for the API.
    
    Returns:
        dict: JSON object with a `message` field indicating service status (e.g. `{"message": "200 corriendo..."}`).
    """
    return {"message": "200 corriendo..."}

