# Archivo: app/models/document.py

from sqlalchemy import Column, Integer, String, DateTime, func
# Importamos la Base centralizada desde nuestra capa de core/database, todavia no esta 
from app.core.database_connection import Base 

class DocumentModel(Base):
    """
    Modelo ORM para la tabla 'documents'.
    Mapea las columnas de PostgreSQL a atributos de Python.
    """
    
    __tablename__ = "documents"

    # id SERIAL PRIMARY KEY -> Integer, Primary Key, autoincrementa
    id = Column(Integer, primary_key=True, index=True)
    
    # filename TEXT NOT NULL -> String, no nulo
    filename = Column(String, nullable=False)
    
    # minio_path TEXT NOT NULL -> String, no nulo. 
    # Usaremos esto para guardar la 's3_key' o 'uploads/file.pdf'
    minio_path = Column(String, nullable=False, unique=True, index=True)
    
    # uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -> DateTime con valor por defecto
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', path='{self.minio_path}')>"
