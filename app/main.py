import logging

from fastapi import FastAPI

from app.api.routes import health, ong, webhook
from app.config import APP_VERSION, settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title=settings.APP_NAME,
    description="Assistente de doações via WhatsApp com IA conversacional",
    version=APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(webhook.router, prefix="/api", tags=["webhook"])
app.include_router(ong.router, prefix="/api", tags=["ongs"])
