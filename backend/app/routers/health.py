"""Health check."""

from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.scraper import check_playwright_available

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", version="0.1.0",
                          playwright_ready=await check_playwright_available())
