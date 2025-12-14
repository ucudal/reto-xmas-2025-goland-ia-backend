import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker


def _req(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v


def _build_database_url() -> URL:
    db_host = _req("DB_HOST")
    try:
        db_port = int(_req("DB_PORT"))
    except ValueError as err:
        raise RuntimeError(
            f"DB_PORT must be a valid integer, got: {os.getenv('DB_PORT')}"
        ) from err
    db_name = _req("DB_NAME")
    db_user = _req("DB_USER")
    db_password = _req("DB_PASSWORD")

    return URL.create(
        "postgresql+psycopg2",
        username=db_user,
        password=db_password,
        host=db_host,
        port=db_port,
        database=db_name,
    )


# Create SQLAlchemy engine
engine = create_engine(_build_database_url(), pool_pre_ping=True)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Database session dependency for FastAPI.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database and verify PGVector extension is available.
    """
    with engine.connect() as conn:
        # Check if pgvector extension exists
        result = conn.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        if not result.scalar():
            raise RuntimeError(
                "PGVector extension is not installed. Please run the init.sql script."
            )
