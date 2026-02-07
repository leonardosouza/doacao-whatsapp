import logging

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session

from app.agent.nodes import (
    classify_node,
    generate_node,
    make_enrich_node,
    retrieve_node,
)
from app.agent.state import ConversationState

logger = logging.getLogger(__name__)


def build_graph(db: Session) -> CompiledStateGraph:
    graph = StateGraph(ConversationState)

    graph.add_node("classify", classify_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("enrich", make_enrich_node(db))
    graph.add_node("generate", generate_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "enrich")
    graph.add_edge("enrich", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


async def process_message(user_message: str, db: Session) -> dict:
    graph = build_graph(db)

    initial_state: ConversationState = {
        "user_message": user_message,
        "intent": "",
        "sentiment": "",
        "rag_context": [],
        "ong_context": "",
        "response": "",
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
