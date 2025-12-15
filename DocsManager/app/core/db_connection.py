import os
from sqlalchemy import create_engine
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

def get_engine():
    return create_engine(_build_database_url(), pool_pre_ping=True)

def get_sessionmaker():
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

Base = declarative_base()
