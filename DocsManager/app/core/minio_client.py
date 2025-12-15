from minio import Minio
from app.core.config import settings

minio_client = Minio(
    "localhost:9000",
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=False
)

BUCKET = "mybucket"

if not minio_client.bucket_exists(BUCKET):
    minio_client.make_bucket(BUCKET)
