from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Armar la URL de conexión
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


engine = create_engine(DATABASE_URL) #aca se guarda la config para la conexion a la db
SessionLocal = sessionmaker(bind=engine) #clase para crear sesiones de conexion a la db (db = SessionLocal())

Base = declarative_base() #clase base para crear los modelos (tablas) de la db y mapearlos con el ORM