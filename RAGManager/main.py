import logging
import time
from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from app.api.routes import documents
from app.core.database_connection import init_db

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
    """Initialize database on startup with retry logic."""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            init_db()
            logging.info("Database initialized successfully")
            return
        except OperationalError as e:
            error_msg = str(e)
            # Check if it's a hostname resolution issue
            if "could not translate host name" in error_msg or "Name or service not known" in error_msg:
                if "db" in error_msg:
                    logging.error(
                        "Database host 'db' not found. When running locally (outside Docker), "
                        "update your .env file to use 'localhost' instead of 'db' in DATABASE_URL.\n"
                        f"Example: DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vectordb"
                    )
                else:
                    logging.error(f"Database host not found: {error_msg}")
            else:
                logging.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                logging.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logging.error("Failed to connect to database after all retries")
                raise
        except RuntimeError as e:
            logging.error(f"Database initialization error: {e}")
            # Don't crash if pgvector is missing - log warning instead
            logging.warning("Continuing without pgvector extension verification")
            return
        except Exception as e:
            logging.error(f"Unexpected error during database initialization: {e}")
            raise


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
def health_check():
    return {"message": "200 corriendo..."}


