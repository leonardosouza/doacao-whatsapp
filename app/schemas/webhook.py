from pydantic import BaseModel


class TextContent(BaseModel):
    message: str
    description: str | None = None
    title: str | None = None
    url: str | None = None


class ZAPIWebhookPayload(BaseModel):
    phone: str
    instanceId: str
    messageId: str
    fromMe: bool = False
    isGroup: bool = False
    senderName: str | None = None
    text: TextContent | None = None

    def get_message_text(self) -> str | None:
        if self.text:
            return self.text.message
        return None


class ZAPISendMessage(BaseModel):
    phone: str
    message: str
