from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/health")
def admin_health():
    return {"status": "ok"}

@router.get("/ping")
def admin_ping():
    return {"pong": True}