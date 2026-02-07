import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ong import OngCreate, OngResponse, OngUpdate
from app.services import ong_service

router = APIRouter()


@router.post("/ongs", response_model=OngResponse, status_code=201)
def create_ong(data: OngCreate, db: Session = Depends(get_db)):
    return ong_service.create_ong(db, data)


@router.get("/ongs", response_model=list[OngResponse])
def list_ongs(
    category: str | None = Query(None, description="Filtrar por categoria"),
    state: str | None = Query(None, description="Filtrar por UF (ex: SP)"),
    city: str | None = Query(None, description="Filtrar por cidade"),
    active_only: bool = Query(True, description="Apenas ONGs ativas"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ong_service.list_ongs(
        db,
        category=category,
        state=state,
        city=city,
        active_only=active_only,
        skip=skip,
        limit=limit,
    )


@router.get("/ongs/{ong_id}", response_model=OngResponse)
def get_ong(ong_id: uuid.UUID, db: Session = Depends(get_db)):
    ong = ong_service.get_ong(db, ong_id)
    if not ong:
        raise HTTPException(status_code=404, detail="ONG não encontrada")
    return ong


@router.put("/ongs/{ong_id}", response_model=OngResponse)
def update_ong(ong_id: uuid.UUID, data: OngUpdate, db: Session = Depends(get_db)):
    ong = ong_service.update_ong(db, ong_id, data)
    if not ong:
        raise HTTPException(status_code=404, detail="ONG não encontrada")
    return ong


@router.delete("/ongs/{ong_id}", response_model=OngResponse)
def delete_ong(ong_id: uuid.UUID, db: Session = Depends(get_db)):
    ong = ong_service.delete_ong(db, ong_id)
    if not ong:
        raise HTTPException(status_code=404, detail="ONG não encontrada")
    return ong
