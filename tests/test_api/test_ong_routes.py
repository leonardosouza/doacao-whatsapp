import uuid


class TestCreateOng:
    def test_success(self, client, auth_headers, sample_ong_data):
        resp = client.post("/api/ongs", json=sample_ong_data, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == sample_ong_data["name"]
        assert data["is_active"] is True
        assert "id" in data

    def test_no_auth_returns_403(self, client, sample_ong_data):
        resp = client.post("/api/ongs", json=sample_ong_data)
        assert resp.status_code == 403

    def test_missing_fields_returns_422(self, client, auth_headers):
        resp = client.post("/api/ongs", json={"name": "X"}, headers=auth_headers)
        assert resp.status_code == 422


class TestListOngs:
    def test_returns_active(self, client, multiple_ongs_in_db):
        resp = client.get("/api/ongs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert all(o["is_active"] for o in data)

    def test_filter_category(self, client, multiple_ongs_in_db):
        resp = client.get("/api/ongs?category=Saúde")
        assert resp.status_code == 200
        data = resp.json()
        assert all("Saúde" in o["category"] for o in data)

    def test_filter_state(self, client, multiple_ongs_in_db):
        resp = client.get("/api/ongs?state=SP")
        data = resp.json()
        assert all(o["state"] == "SP" for o in data)

    def test_pagination(self, client, multiple_ongs_in_db):
        resp = client.get("/api/ongs?skip=1&limit=2")
        data = resp.json()
        assert len(data) == 2


class TestGetOng:
    def test_found(self, client, sample_ong_in_db):
        resp = client.get(f"/api/ongs/{sample_ong_in_db.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == sample_ong_in_db.name

    def test_not_found(self, client):
        resp = client.get(f"/api/ongs/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "ONG não encontrada"


class TestUpdateOng:
    def test_success(self, client, auth_headers, sample_ong_in_db):
        resp = client.put(
            f"/api/ongs/{sample_ong_in_db.id}",
            json={"name": "Novo Nome"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Novo Nome"

    def test_not_found(self, client, auth_headers):
        resp = client.put(
            f"/api/ongs/{uuid.uuid4()}",
            json={"name": "Inexistente"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "ONG não encontrada"


class TestDeleteOng:
    def test_soft_delete(self, client, auth_headers, sample_ong_in_db):
        resp = client.delete(
            f"/api/ongs/{sample_ong_in_db.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        # Verify excluded from active list
        list_resp = client.get("/api/ongs")
        names = [o["name"] for o in list_resp.json()]
        assert sample_ong_in_db.name not in names

    def test_not_found(self, client, auth_headers):
        resp = client.delete(
            f"/api/ongs/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "ONG não encontrada"
