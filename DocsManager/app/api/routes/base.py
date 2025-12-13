from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Hello World"}

@router.get("/health")
def health_check():
    return {"message": "200 corriendo..."}

