import mimetypes
from fastapi import FastAPI, UploadFile, File, HTTPException
from sqlalchemy.exc import OperationalError
from app.api.routes.files import router as admin_router
from app.core.database_connection import engine, Base
from fastapi.responses import StreamingResponse
from minio import Minio

from app.api.routes.files import router as files_router

app = FastAPI()

app.include_router(files_router)

Base.metadata.create_all(bind=engine)

app.include_router(admin_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
def health_check():
   return {"message": "200 corriendo..."}


# Conectamos MinIO con FastApi

minio_client = Minio(
    "localhost:9000",      
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)


BUCKET = "mybucket"

if not minio_client.bucket_exists(BUCKET):
    minio_client.make_bucket(BUCKET)



# @app.get("/files")
# def list_files():
#     try:
#         files = minio_client.list_objects(BUCKET, recursive=True)
#         return [obj.object_name for obj in files]
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    
# @app.get("/view/{file_name}")
# def view_file(file_name: str):
#     try:
#         file = minio_client.get_object(BUCKET, file_name)

#         mime_type, _ = mimetypes.guess_type(file_name)
#         mime_type = mime_type or "application/octet-stream"

#         return StreamingResponse(
#             file,
#             media_type=mime_type,
#             headers={
#                 "Content-Disposition": f'inline; filename="{file_name}"'
#             }
#         )

#     except Exception as e:
#         raise HTTPException(status_code=404, detail=str(e))


# @app.get("/download/{file_name}")
# def download_file(file_name: str):
#     try:
#         file = minio_client.get_object(BUCKET, file_name)
#         return StreamingResponse(
#             file,
#             media_type="application/octet-stream",
#             headers={
#                 "Content-Disposition": f"attachment; filename={file_name}"
#             }
#         )
#     except Exception as e:
#         raise HTTPException(status_code=404, detail=str(e))


# @app.post("/upload")
# async def upload_file(file: UploadFile = File(...)):
#     try:
#         data = await file.read()

#         minio_client.put_object(
#             BUCKET,
#             file.filename,
#             data=data,
#             length=len(data),
#             content_type=file.content_type
#         )

#         return {"uploaded": file.filename}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))



