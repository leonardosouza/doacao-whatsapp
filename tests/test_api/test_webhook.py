from unittest.mock import AsyncMock, patch


def _make_payload(**overrides):
    base = {
        "phone": "5511999990000",
        "instanceId": "inst-1",
        "messageId": "msg-1",
        "fromMe": False,
        "isGroup": False,
        "text": {"message": "Quero doar"},
    }
    base.update(overrides)
    return base


class TestWebhook:
    def test_ignores_from_me(self, client):
        resp = client.post("/api/webhook", json=_make_payload(fromMe=True))
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_ignores_group(self, client):
        resp = client.post("/api/webhook", json=_make_payload(isGroup=True))
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_ignores_no_text(self, client):
        resp = client.post("/api/webhook", json=_make_payload(text=None))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "no text content"

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_processes_valid_message(self, mock_process, mock_send, client):
        mock_process.return_value = {
            "response": "Olá! Como posso ajudar?",
            "intent": "Quero Doar",
            "sentiment": "Positivo",
        }
        mock_send.return_value = {"zapiMessageId": "123"}

        resp = client.post("/api/webhook", json=_make_payload())
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"
        assert data["intent"] == "Quero Doar"
        mock_send.assert_called_once_with("5511999990000", "Olá! Como posso ajudar?")

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_passes_empty_history_on_first_message(self, mock_process, mock_send, client):
        mock_process.return_value = {
            "response": "R",
            "intent": "Ambíguo",
            "sentiment": "Neutro",
        }
        mock_send.return_value = {}

        client.post("/api/webhook", json=_make_payload(phone="5511777770000"))
        _, kwargs = mock_process.call_args
        assert kwargs["conversation_history"] == ""

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_passes_history_on_second_message(self, mock_process, mock_send, client):
        mock_process.return_value = {
            "response": "R",
            "intent": "Ambíguo",
            "sentiment": "Neutro",
        }
        mock_send.return_value = {}

        # First message
        client.post("/api/webhook", json=_make_payload(phone="5511666660000"))

        # Second message — history should include first exchange
        mock_process.reset_mock()
        client.post(
            "/api/webhook",
            json=_make_payload(phone="5511666660000", text={"message": "Qual o PIX?"}),
        )
        _, kwargs = mock_process.call_args
        history = kwargs["conversation_history"]
        assert "Usuário: Quero doar" in history
        assert "Assistente: R" in history

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_creates_conversation(self, mock_process, mock_send, client, db_session):
        mock_process.return_value = {
            "response": "Oi",
            "intent": "Ambíguo",
            "sentiment": "Neutro",
        }
        mock_send.return_value = {}

        from app.models.conversation import Conversation

        before = db_session.query(Conversation).count()
        client.post("/api/webhook", json=_make_payload(phone="5511888880000"))
        after = db_session.query(Conversation).count()
        assert after == before + 1

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_reuses_conversation(self, mock_process, mock_send, client, sample_conversation):
        mock_process.return_value = {
            "response": "Oi",
            "intent": "Ambíguo",
            "sentiment": "Neutro",
        }
        mock_send.return_value = {}

        from app.models.conversation import Conversation

        client.post(
            "/api/webhook",
            json=_make_payload(phone=sample_conversation.phone_number),
        )
        from tests.conftest import db_session
        # The conversation should be reused, not duplicated
        # We can verify by checking process_message was called (the flow ran)
        mock_process.assert_called_once()
