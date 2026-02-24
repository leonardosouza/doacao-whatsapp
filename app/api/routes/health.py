from enum import Enum

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import APP_VERSION
from app.database import get_db
from app.services import zapi_service

router = APIRouter()


class StatusEnum(str, Enum):
    ok = "ok"
    degraded = "degraded"


class ConnectionEnum(str, Enum):
    connected = "connected"
    disconnected = "disconnected"


class HealthResponse(BaseModel):
    status: StatusEnum
    version: str
    database: ConnectionEnum
    zapi: ConnectionEnum


async def _health_check(db: Session) -> dict:
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    zapi_result = await zapi_service.get_status()
    zapi_connected = zapi_result.get("connected", False)
    zapi_status = "connected" if zapi_connected else "disconnected"

    all_ok = db_status == "connected" and zapi_connected
    status = "ok" if all_ok else "degraded"

    return {
        "status": status,
        "version": APP_VERSION,
        "database": db_status,
        "zapi": zapi_status,
    }


@router.get("/health", response_model=HealthResponse)
async def health_check_get(db: Session = Depends(get_db)):
    return await _health_check(db)


@router.post("/health", response_model=HealthResponse)
async def health_check_post(db: Session = Depends(get_db)):
    return await _health_check(db)
