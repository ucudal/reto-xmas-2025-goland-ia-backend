"""API routes package."""

from fastapi import APIRouter

from app.api.routes import documents

router = APIRouter(prefix="/api/v1")

router.include_router(documents.router)