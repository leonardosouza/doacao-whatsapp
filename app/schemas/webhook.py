from pydantic import BaseModel


class TextContent(BaseModel):
    message: str
    description: str | None = None
    title: str | None = None
    url: str | None = None


class AudioContent(BaseModel):
    audioUrl: str
    mimeType: str | None = None
    seconds: int | None = None
    ptt: bool | None = None  # push-to-talk (gravação de voz)


class VideoContent(BaseModel):
    videoUrl: str
    caption: str | None = None
    mimeType: str | None = None
    seconds: int | None = None


class ImageContent(BaseModel):
    imageUrl: str
    caption: str | None = None
    mimeType: str | None = None


class DocumentContent(BaseModel):
    documentUrl: str
    caption: str | None = None
    mimeType: str | None = None
    fileName: str | None = None


class StickerContent(BaseModel):
    stickerUrl: str
    mimeType: str | None = None


class ZAPIWebhookPayload(BaseModel):
    phone: str
    instanceId: str
    messageId: str
    fromMe: bool = False
    isGroup: bool = False
    senderName: str | None = None
    text: TextContent | None = None
    audio: AudioContent | None = None
    video: VideoContent | None = None
    image: ImageContent | None = None
    document: DocumentContent | None = None
    sticker: StickerContent | None = None

    def get_message_text(self) -> str | None:
        if self.text:
            return self.text.message
        return None

    def get_media_type(self) -> str | None:
        if self.audio:
            return "audio"
        if self.video:
            return "video"
        if self.image:
            return "image"
        if self.document:
            return "document"
        if self.sticker:
            return "sticker"
        return None


class ZAPISendMessage(BaseModel):
    phone: str
    message: str


class WebhookResponse(BaseModel):
    status: str
    reason: str | None = None
    intent: str | None = None
