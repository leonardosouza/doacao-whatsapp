from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services import zapi_service


class TestGetStatus:
    @pytest.mark.asyncio
    async def test_connected(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"connected": True}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.zapi_service.httpx.AsyncClient", return_value=mock_client):
            result = await zapi_service.get_status()

        assert result["connected"] is True

    @pytest.mark.asyncio
    async def test_http_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=MagicMock())
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.zapi_service.httpx.AsyncClient", return_value=mock_client):
            result = await zapi_service.get_status()

        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_connection_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.zapi_service.httpx.AsyncClient", return_value=mock_client):
            result = await zapi_service.get_status()

        assert result["connected"] is False


class TestSendTextMessage:
    @pytest.mark.asyncio
    async def test_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"zapiMessageId": "123", "messageId": "456"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.zapi_service.httpx.AsyncClient", return_value=mock_client):
            result = await zapi_service.send_text_message("5511999990000", "Olá")

        assert result["zapiMessageId"] == "123"

    @pytest.mark.asyncio
    async def test_failure_returns_none(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=MagicMock())
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.zapi_service.httpx.AsyncClient", return_value=mock_client):
            result = await zapi_service.send_text_message("5511999990000", "Olá")

        assert result is None
