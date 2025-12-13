# Archivo: app/api/routes/admin.py (Controller)

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from sqlalchemy.orm import Session # Tipo de dato para la sesión DB
from minio import Minio # Solo para tipado

# Importar las dependencias desde tu arquitectura (deps.py)
from app.api.deps import get_db, get_minio_client, get_current_user 
# Importar la función del servicio
from app.services import admin as admin_service
# Importar el Response Model
from app.schemas.document import DocumentUploadResponse 

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post(
    "/upload-document", 
    response_model=DocumentUploadResponse, 
    status_code=status.HTTP_201_CREATED
)
def upload_document_route(
    # 1. Entrada HTTP: El archivo
    file: UploadFile = File(...),              
    
    # 2. Dependencias: Cliente DB y MinIO
    db: Session = Depends(get_db),
    minio_client: Minio = Depends(get_minio_client), 
    
):
    """
    Endpoint para subir un documento. Delega la lógica de subida (MinIO) 
    y registro (Postgres) a la capa de servicio.
    """
    
    # 1. Extracción de Datos y Pre-validación
    file_content = file.file.read()

    # Chequeo de que el archivo no esté vacío (validación de negocio/protocolo)
    if not file_content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file cannot be empty.")
        
    try:
        # 2. Delegación al Servicio
        # Se pasa el cliente MinIO, la sesión DB, y los datos puros (bytes, nombre, user_id)
        document_record = admin_service.upload_document(
            db=db, 
            minio_client=minio_client,
            file_content=file_content,
            filename=file.filename,
        )
        
        # 3. Retorno
        # El servicio retorna el objeto ORM, que FastAPI mapea al ResponseModel
        return document_record
        
    except HTTPException:
        # Si el servicio lanza una HTTPException (502 de MinIO, 500 de DB), la propagamos
        raise
    except Exception as e:
        # Captura cualquier error no controlado y lo convierte en 500
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal Server Error: {str(e)}")
