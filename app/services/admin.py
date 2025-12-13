import os 
from sqlalchemy.orm import Session
from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException, status
import io
from dotenv import load_dotenv

from app.models.document import DocumentModel
from app.schemas.document import DocumentUploadResponse

load_dotenv() # Carga las variables desde el .env

def upload_document(
    db: Session, 
    minio_client: Minio, 
    file_content: bytes, 
    filename: str,
) -> DocumentUploadResponse:
    
    bucket_name = os.getenv("MINIO_BUCKET_NAME") 
    
    if not bucket_name:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de configuración: MINIO_BUCKET_NAME no está definido."
        )
    # -----------------------------------------------------------
    
    s3_key = f"uploads/{filename}"
    file_size = len(file_content)
    
    try:
        # 1. Subida a MinIO
        data_stream = io.BytesIO(file_content)
        
        minio_client.put_object(
            bucket_name,
            s3_key,
            data_stream,
            length=file_size,
            content_type='application/octet-stream'
        )
        print(f"File {s3_key} uploaded successfully to MinIO.")
        
        # 2. Registro en la Base de Datos
        db_document = DocumentModel(
            s3_key=s3_key,
            filename=filename,
        )
        
        db.add(db_document)
        db.commit() 
        db.refresh(db_document)
        
        # 3. Retorno del Response Model
        return db_document
        
    except S3Error as e:
        db.rollback() 
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al subir archivo a MinIO: {e.code}"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error interno durante el procesamiento: {str(e)}"
        )
