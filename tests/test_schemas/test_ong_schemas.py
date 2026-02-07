import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.schemas.ong import OngCreate, OngResponse, OngUpdate


class TestOngCreate:
    def test_required_only(self):
        data = OngCreate(name="X", category="Y", city="Z", state="SP")
        assert data.name == "X"
        assert data.pix_key is None
        assert data.website is None

    def test_missing_required(self):
        with pytest.raises(ValidationError):
            OngCreate(category="Y", city="Z", state="SP")

    def test_all_fields(self):
        data = OngCreate(
            name="ONG",
            category="Saúde",
            subcategory="Infantil",
            city="SP",
            state="SP",
            phone="11999990000",
            website="https://ong.org",
            email="a@b.com",
            pix_key="pix@ong.org",
            bank_info="Banco X",
            donation_url="https://doe.org",
        )
        dump = data.model_dump()
        assert dump["subcategory"] == "Infantil"
        assert dump["pix_key"] == "pix@ong.org"


class TestOngUpdate:
    def test_all_optional(self):
        data = OngUpdate()
        assert data.model_dump(exclude_unset=True) == {}

    def test_partial(self):
        data = OngUpdate(name="Novo Nome")
        dump = data.model_dump(exclude_unset=True)
        assert dump == {"name": "Novo Nome"}


class TestOngResponse:
    def test_from_attributes(self):
        mock_ong = MagicMock()
        mock_ong.id = uuid.uuid4()
        mock_ong.name = "ONG Teste"
        mock_ong.category = "Saúde"
        mock_ong.subcategory = None
        mock_ong.city = "SP"
        mock_ong.state = "SP"
        mock_ong.phone = None
        mock_ong.website = None
        mock_ong.email = None
        mock_ong.pix_key = None
        mock_ong.bank_info = None
        mock_ong.donation_url = None
        mock_ong.is_active = True
        mock_ong.created_at = datetime.now(timezone.utc)
        mock_ong.updated_at = datetime.now(timezone.utc)

        resp = OngResponse.model_validate(mock_ong, from_attributes=True)
        assert resp.name == "ONG Teste"
        assert resp.is_active is True
