import uuid
from datetime import datetime

from pydantic import BaseModel


class OngCreate(BaseModel):
    name: str
    category: str
    subcategory: str | None = None
    city: str
    state: str
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    pix_key: str | None = None
    bank_info: str | None = None
    donation_url: str | None = None


class OngUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    subcategory: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    pix_key: str | None = None
    bank_info: str | None = None
    donation_url: str | None = None
    is_active: bool | None = None


class OngResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    subcategory: str | None
    city: str
    state: str
    phone: str | None
    website: str | None
    email: str | None
    pix_key: str | None
    bank_info: str | None
    donation_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
