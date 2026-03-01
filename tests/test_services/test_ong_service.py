import uuid

from app.schemas.ong import OngCreate, OngUpdate
from app.services import ong_service


class TestCreateOng:
    def test_create(self, db_session):
        data = OngCreate(name="ONG Nova", category="Saúde", city="SP", state="SP")
        ong = ong_service.create_ong(db_session, data)
        assert ong.id is not None
        assert ong.name == "ONG Nova"
        assert ong.is_active is True


class TestGetOng:
    def test_found(self, db_session, sample_ong_in_db):
        ong = ong_service.get_ong(db_session, sample_ong_in_db.id)
        assert ong is not None
        assert ong.name == sample_ong_in_db.name

    def test_not_found(self, db_session):
        ong = ong_service.get_ong(db_session, uuid.uuid4())
        assert ong is None


class TestListOngs:
    def test_active_only(self, db_session, multiple_ongs_in_db):
        result = ong_service.list_ongs(db_session)
        assert len(result) == 5  # 6 total, 1 inactive
        names = [o.name for o in result]
        assert "ONG Inativa F" not in names

    def test_include_inactive(self, db_session, multiple_ongs_in_db):
        result = ong_service.list_ongs(db_session, active_only=False)
        assert len(result) == 6

    def test_filter_category(self, db_session, multiple_ongs_in_db):
        result = ong_service.list_ongs(db_session, category="Saúde")
        assert all("Saúde" in o.category for o in result)

    def test_filter_state(self, db_session, multiple_ongs_in_db):
        result = ong_service.list_ongs(db_session, state="SP")
        assert all(o.state == "SP" for o in result)

    def test_filter_city(self, db_session, multiple_ongs_in_db):
        result = ong_service.list_ongs(db_session, city="São Paulo")
        assert all("São Paulo" in o.city for o in result)

    def test_pagination(self, db_session, multiple_ongs_in_db):
        all_ongs = ong_service.list_ongs(db_session)
        page = ong_service.list_ongs(db_session, skip=2, limit=2)
        assert len(page) == 2
        assert page[0].name == all_ongs[2].name

    def test_ordered_by_name(self, db_session, multiple_ongs_in_db):
        result = ong_service.list_ongs(db_session)
        names = [o.name for o in result]
        assert names == sorted(names)

    def test_filter_q_by_name(self, db_session, multiple_ongs_in_db):
        result = ong_service.list_ongs(db_session, q="Animais")
        assert len(result) == 1
        assert result[0].name == "ONG Animais C"

    def test_filter_q_by_subcategory(self, db_session):
        from app.models.ong import Ong as OngModel
        ong = OngModel(
            name="Floresta Viva",
            category="Meio Ambiente",
            city="Manaus",
            state="AM",
            subcategory="preservacao da floresta amazonica",
        )
        db_session.add(ong)
        db_session.commit()
        result = ong_service.list_ongs(db_session, q="amazonica")
        assert any(o.name == "Floresta Viva" for o in result)

    def test_filter_q_no_match(self, db_session, multiple_ongs_in_db):
        result = ong_service.list_ongs(db_session, q="xyznotfound999")
        assert len(result) == 0

    def test_filter_name_partial(self, db_session, multiple_ongs_in_db):
        result = ong_service.list_ongs(db_session, name="Fome")
        assert len(result) == 1
        assert result[0].name == "ONG Fome A"

    def test_filter_name_no_match(self, db_session):
        result = ong_service.list_ongs(db_session, name="inexistente_xyz")
        assert len(result) == 0

    def test_filter_q_escapes_percent_wildcard(self, db_session, multiple_ongs_in_db):
        # "%" must be treated as literal, not SQL wildcard
        result = ong_service.list_ongs(db_session, q="%")
        assert len(result) == 0


class TestUpdateOng:
    def test_partial_update(self, db_session, sample_ong_in_db):
        data = OngUpdate(name="Novo Nome")
        ong = ong_service.update_ong(db_session, sample_ong_in_db.id, data)
        assert ong.name == "Novo Nome"
        assert ong.category == sample_ong_in_db.category  # unchanged

    def test_not_found(self, db_session):
        data = OngUpdate(name="Inexistente")
        result = ong_service.update_ong(db_session, uuid.uuid4(), data)
        assert result is None


class TestDeleteOng:
    def test_soft_delete(self, db_session, sample_ong_in_db):
        ong = ong_service.delete_ong(db_session, sample_ong_in_db.id)
        assert ong.is_active is False
        # Still in DB
        found = ong_service.get_ong(db_session, sample_ong_in_db.id)
        assert found is not None

    def test_not_found(self, db_session):
        result = ong_service.delete_ong(db_session, uuid.uuid4())
        assert result is None
