from fastapi import FastAPI

from app.api.routes import health
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Assistente de doações via WhatsApp com IA conversacional",
    version="0.1.0",
)

app.include_router(health.router, prefix="/api", tags=["health"])
