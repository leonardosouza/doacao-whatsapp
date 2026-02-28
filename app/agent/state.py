from typing import TypedDict


class ConversationState(TypedDict):
    user_message: str
    conversation_history: str
    intent: str
    sentiment: str
    rag_context: list[dict]
    ong_context: str
    response: str
    user_name: str | None
    user_email: str | None
    profile_stage: str  # "collecting_name" | "collecting_email" | "complete"
