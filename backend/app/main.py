"""ConvertMyChat API — Extract, export, and manage Gemini conversations."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine
from app.models import Base
from app.routers import health, export, auth, history, admin

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified")
    except Exception as e:
        logger.warning(f"Database init failed (will retry on first request): {e}")
    yield
    await engine.dispose()
    logger.info("Shut down")


app = FastAPI(
    title=settings.app_name,
    description="Extract and export Gemini shared conversations",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(export.router, prefix="/api", tags=["export"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(history.router, prefix="/api/history", tags=["history"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# Serve React SPA in production (Docker build copies frontend/dist → /app/static)
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
