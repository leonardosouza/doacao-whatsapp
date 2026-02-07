from unittest.mock import AsyncMock, MagicMock, patch

from app.database import get_db


class TestHealthCheck:
    @patch("app.api.routes.health.zapi_service.get_status", new_callable=AsyncMock)
    def test_all_ok(self, mock_zapi, client):
        mock_zapi.return_value = {"connected": True}
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"
        assert data["zapi"] == "connected"

    @patch("app.api.routes.health.zapi_service.get_status", new_callable=AsyncMock)
    def test_zapi_disconnected(self, mock_zapi, client):
        mock_zapi.return_value = {"connected": False}
        resp = client.get("/api/health")
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["database"] == "connected"
        assert data["zapi"] == "disconnected"

    @patch("app.api.routes.health.zapi_service.get_status", new_callable=AsyncMock)
    def test_db_disconnected(self, mock_zapi, client, db_session):
        mock_zapi.return_value = {"connected": True}

        from fastapi import FastAPI
        from app.main import app as fastapi_app

        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("DB down")

        def override_get_db():
            yield mock_session

        fastapi_app.dependency_overrides[get_db] = override_get_db
        resp = client.get("/api/health")
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
        assert data["zapi"] == "connected"

    @patch("app.api.routes.health.zapi_service.get_status", new_callable=AsyncMock)
    def test_both_disconnected(self, mock_zapi, client, db_session):
        mock_zapi.return_value = {"connected": False}

        from app.main import app as fastapi_app

        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("DB down")

        def override_get_db():
            yield mock_session

        fastapi_app.dependency_overrides[get_db] = override_get_db
        resp = client.get("/api/health")
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
        assert data["zapi"] == "disconnected"
