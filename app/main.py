import logging
import zoneinfo
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, ong, webhook
from app.config import APP_VERSION, settings


class _SPFormatter(logging.Formatter):
    """Formata timestamps dos logs no fuso horário de São Paulo (UTC-3)."""

    _tz = zoneinfo.ZoneInfo("America/Sao_Paulo")

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=self._tz)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S") + f",{record.msecs:03.0f}"


_handler = logging.StreamHandler()
_handler.setFormatter(_SPFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])

app = FastAPI(
    title=settings.APP_NAME,
    description="Assistente de doações via WhatsApp com IA conversacional",
    version=APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://doacao-whatsapp.onrender.com",
        "https://doazap-dashboard.onrender.com",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(webhook.router, prefix="/api", tags=["webhook"])
app.include_router(ong.router, prefix="/api", tags=["ongs"])
