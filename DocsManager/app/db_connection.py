import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker


def _req(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v


DB_HOST = _req("DB_HOST")

try:
    DB_PORT = int(_req("DB_PORT"))
except ValueError:
    raise RuntimeError(f"DB_PORT must be a valid integer, got: {os.getenv('DB_PORT')}")

DB_NAME = _req("DB_NAME")
DB_USER = _req("DB_USER")
DB_PASSWORD = _req("DB_PASSWORD")


DATABASE_URL = URL.create(
    "postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(
bind=engine,
autoflush=False,
autocommit=False,
expire_on_commit=False, )

Base = declarative_base()
