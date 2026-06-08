from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Multi-agent AI API for StartMate AI.",
    )
    app.include_router(router)
    return app


app = create_app()
