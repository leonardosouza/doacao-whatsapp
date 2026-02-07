import logging
import uuid

from sqlalchemy.orm import Session

from app.models.ong import Ong
from app.schemas.ong import OngCreate, OngUpdate

logger = logging.getLogger(__name__)


def create_ong(db: Session, data: OngCreate) -> Ong:
    ong = Ong(**data.model_dump())
    db.add(ong)
    db.commit()
    db.refresh(ong)
    logger.info(f"ONG criada: {ong.name} (id={ong.id})")
    return ong


def get_ong(db: Session, ong_id: uuid.UUID) -> Ong | None:
    return db.query(Ong).filter(Ong.id == ong_id).first()


def list_ongs(
    db: Session,
    category: str | None = None,
    state: str | None = None,
    city: str | None = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 50,
) -> list[Ong]:
    query = db.query(Ong)

    if active_only:
        query = query.filter(Ong.is_active.is_(True))
    if category:
        query = query.filter(Ong.category.ilike(f"%{category}%"))
    if state:
        query = query.filter(Ong.state == state.upper())
    if city:
        query = query.filter(Ong.city.ilike(f"%{city}%"))

    return query.order_by(Ong.name).offset(skip).limit(limit).all()


def update_ong(db: Session, ong_id: uuid.UUID, data: OngUpdate) -> Ong | None:
    ong = get_ong(db, ong_id)
    if not ong:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ong, field, value)

    db.commit()
    db.refresh(ong)
    logger.info(f"ONG atualizada: {ong.name} (id={ong.id})")
    return ong


def delete_ong(db: Session, ong_id: uuid.UUID) -> Ong | None:
    ong = get_ong(db, ong_id)
    if not ong:
        return None

    ong.is_active = False
    db.commit()
    db.refresh(ong)
    logger.info(f"ONG desativada: {ong.name} (id={ong.id})")
    return ong
