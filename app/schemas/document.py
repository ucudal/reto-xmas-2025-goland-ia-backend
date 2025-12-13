from pydantic import BaseModel, ConfigDict
from datetime import datetime

# ----------------------------------------------------------------------
# 1. Esquema Base
# ----------------------------------------------------------------------

class DocumentBase(BaseModel):
    """Campos base que identifican el documento."""
    filename: str
    minio_path: str 
    status: str 
    

# ----------------------------------------------------------------------
# 2. Esquema de Respuesta de Subida (El response_model para el POST)
# ----------------------------------------------------------------------

class DocumentUploadResponse(DocumentBase):
    """
    Define la estructura de los datos retornados después de crear un nuevo documento.
    (response_model para POST /upload-document).
    """
    id: int
    uploaded_at: datetime
    
    # Configuración crucial para que Pydantic pueda leer los datos 
    # directamente desde el objeto ORM (db_document)
    model_config = ConfigDict(from_attributes=True) 
