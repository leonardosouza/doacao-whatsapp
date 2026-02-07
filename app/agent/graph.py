import logging

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.nodes import classify_node, generate_node, retrieve_node
from app.agent.state import ConversationState

logger = logging.getLogger(__name__)


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(ConversationState)

    graph.add_node("classify", classify_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# Singleton do grafo compilado
conversation_graph = build_graph()


async def process_message(user_message: str) -> dict:
    initial_state: ConversationState = {
        "user_message": user_message,
        "intent": "",
        "sentiment": "",
        "rag_context": [],
        "response": "",
    }

    result = await conversation_graph.ainvoke(initial_state)

    logger.info(
        f"Mensagem processada: intent={result['intent']}, "
        f"sentiment={result['sentiment']}"
    )

    return {
        "response": result["response"],
        "intent": result["intent"],
        "sentiment": result["sentiment"],
    }
