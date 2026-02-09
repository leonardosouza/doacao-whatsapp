from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import APP_VERSION
from app.database import get_db
from app.services import zapi_service

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
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
