from typing import TypedDict


class ConversationState(TypedDict):
    user_message: str
    intent: str
    sentiment: str
    rag_context: list[dict]
    ong_context: str
    response: str
