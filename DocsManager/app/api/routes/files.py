from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from minio.error import S3Error

import mimetypes

from app.core.database_connection import get_db
from app.models.document import Document
from app.core.minio_client import minio_client

router = APIRouter(prefix="/files", tags=["Files"])

BUCKET_NAME = "mybucket"

# ------- Recupera los docs de a tandas --------
# GET /files?limit=10&offset=0
@router.get("/")
def list_files(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    documents = (
        db.query(Document)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return documents



@router.get("/{id}")
def get_file(id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    return doc


# ----------- Si "download" es verdadero, se descarga el doc, sino, se muestra
# /files/1/docs?download=true
@router.get("/{id}/docs")
def view_file(
    id: int,
    download: bool = False,
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    try:
        obj = minio_client.get_object("mybucket", doc.minio_path)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado en MinIO"
        )

    content_type, _ = mimetypes.guess_type(doc.filename)
    if not content_type:
        content_type = "application/octet-stream"

    disposition = "attachment" if download else "inline"

    return StreamingResponse(
        obj,
        media_type=content_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{doc.filename}"'
        }
    )
