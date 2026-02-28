import pytest
from pydantic import ValidationError

from app.schemas.webhook import (
    AudioContent,
    DocumentContent,
    ImageContent,
    StickerContent,
    TextContent,
    VideoContent,
    ZAPIWebhookPayload,
    ZAPISendMessage,
)


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

    def _base(self, **kwargs):
        return {"phone": "5511999990000", "instanceId": "inst-1", "messageId": "msg-1", **kwargs}

    def test_get_media_type_none_for_text(self):
        p = ZAPIWebhookPayload(**self._base(text=TextContent(message="Oi")))
        assert p.get_media_type() is None

    def test_get_media_type_none_when_empty(self):
        p = ZAPIWebhookPayload(**self._base())
        assert p.get_media_type() is None

    def test_get_media_type_audio(self):
        p = ZAPIWebhookPayload(**self._base(audio=AudioContent(audioUrl="https://a.com/a.ogg")))
        assert p.get_media_type() == "audio"

    def test_get_media_type_video(self):
        p = ZAPIWebhookPayload(**self._base(video=VideoContent(videoUrl="https://a.com/v.mp4")))
        assert p.get_media_type() == "video"

    def test_get_media_type_image(self):
        p = ZAPIWebhookPayload(**self._base(image=ImageContent(imageUrl="https://a.com/i.jpg")))
        assert p.get_media_type() == "image"

    def test_get_media_type_document(self):
        p = ZAPIWebhookPayload(**self._base(document=DocumentContent(documentUrl="https://a.com/d.pdf")))
        assert p.get_media_type() == "document"

    def test_get_media_type_sticker(self):
        p = ZAPIWebhookPayload(**self._base(sticker=StickerContent(stickerUrl="https://a.com/s.webp")))
        assert p.get_media_type() == "sticker"


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
