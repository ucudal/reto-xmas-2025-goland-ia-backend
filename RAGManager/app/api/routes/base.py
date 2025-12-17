from fastapi import APIRouter

router = APIRouter(tags=["base"])

@router.get("/")
async def root():
    return {"message": "RAGManager up"}

@router.get("/health")
def health_check():
    return {"message": "200 running..."}
