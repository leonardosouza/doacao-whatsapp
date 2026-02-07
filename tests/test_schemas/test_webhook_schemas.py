import pytest
from pydantic import ValidationError

from app.schemas.webhook import TextContent, ZAPIWebhookPayload, ZAPISendMessage


class TestZAPIWebhookPayload:
    def test_get_message_text_with_text(self):
        payload = ZAPIWebhookPayload(
            phone="5511999990000",
            instanceId="inst-1",
            messageId="msg-1",
            text=TextContent(message="Olá"),
        )
        assert payload.get_message_text() == "Olá"

    def test_get_message_text_without_text(self):
        payload = ZAPIWebhookPayload(
            phone="5511999990000",
            instanceId="inst-1",
            messageId="msg-1",
        )
        assert payload.get_message_text() is None

    def test_payload_defaults(self):
        payload = ZAPIWebhookPayload(
            phone="5511999990000",
            instanceId="inst-1",
            messageId="msg-1",
        )
        assert payload.fromMe is False
        assert payload.isGroup is False
        assert payload.senderName is None
        assert payload.text is None

    def test_payload_rejects_missing_required(self):
        with pytest.raises(ValidationError):
            ZAPIWebhookPayload()


class TestTextContent:
    def test_optional_fields(self):
        tc = TextContent(message="hi")
        assert tc.description is None
        assert tc.title is None
        assert tc.url is None


class TestZAPISendMessage:
    def test_requires_phone_and_message(self):
        msg = ZAPISendMessage(phone="5511999990000", message="Olá")
        assert msg.phone == "5511999990000"
        assert msg.message == "Olá"

    def test_rejects_missing_fields(self):
        with pytest.raises(ValidationError):
            ZAPISendMessage()
