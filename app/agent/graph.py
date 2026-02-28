import logging

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session

from app.agent.nodes import (
    classify_node,
    generate_node,
    make_enrich_node,
    make_profile_node,
    profile_response_node,
    retrieve_node,
    route_profile,
)
from app.agent.state import ConversationState
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)


def build_graph(db: Session, conversation: Conversation) -> CompiledStateGraph:
    graph = StateGraph(ConversationState)

    graph.add_node("profile",          make_profile_node(db, conversation))
    graph.add_node("profile_response", profile_response_node)
    graph.add_node("classify",         classify_node)
    graph.add_node("retrieve",         retrieve_node)
    graph.add_node("enrich",           make_enrich_node(db))
    graph.add_node("generate",         generate_node)

    graph.set_entry_point("profile")
    graph.add_conditional_edges("profile", route_profile, {
        "profile_response": "profile_response",
        "classify":         "classify",
    })
    graph.add_edge("profile_response", END)
    graph.add_edge("classify",  "retrieve")
    graph.add_edge("retrieve",  "enrich")
    graph.add_edge("enrich",    "generate")
    graph.add_edge("generate",  END)

    return graph.compile()


async def process_message(
    user_message: str,
    db: Session,
    conversation_history: str = "",
    conversation: Conversation = None,
) -> dict:
    graph = build_graph(db, conversation)

    initial_state: ConversationState = {
        "user_message": user_message,
        "conversation_history": conversation_history,
        "intent": "",
        "sentiment": "",
        "rag_context": [],
        "ong_context": "",
        "response": "",
        "user_name": conversation.user_name if conversation else None,
        "user_email": conversation.user_email if conversation else None,
        "profile_stage": "complete",  # sobrescrito pelo profile_node
    }

    result = await graph.ainvoke(initial_state)

    logger.info(
        f"Mensagem processada: intent={result['intent']}, "
        f"sentiment={result['sentiment']}"
    )

    return {
        "response": result["response"],
        "intent": result["intent"],
        "sentiment": result["sentiment"],
    }
