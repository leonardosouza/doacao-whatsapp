import json
import logging

from langchain_openai import ChatOpenAI

from app.agent.prompts import CLASSIFY_PROMPT, GENERATE_PROMPT
from app.agent.state import ConversationState
from app.config import settings
from app.rag.retriever import retrieve_similar

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    openai_api_key=settings.OPENAI_API_KEY,
)


def classify_node(state: ConversationState) -> dict:
    prompt = CLASSIFY_PROMPT.format(user_message=state["user_message"])
    response = llm.invoke(prompt)

    try:
        classification = json.loads(response.content)
        intent = classification.get("intent", "Ambíguo")
        sentiment = classification.get("sentiment", "Neutro")
    except (json.JSONDecodeError, AttributeError):
        logger.warning(f"Falha ao parsear classificação: {response.content}")
        intent = "Ambíguo"
        sentiment = "Neutro"

    logger.info(f"Classificação: intent={intent}, sentiment={sentiment}")
    return {"intent": intent, "sentiment": sentiment}


def retrieve_node(state: ConversationState) -> dict:
    results = retrieve_similar(state["user_message"], k=3)
    return {"rag_context": results}


def generate_node(state: ConversationState) -> dict:
    rag_text = "\n\n---\n\n".join(
        item["content"] for item in state["rag_context"]
    )

    prompt = GENERATE_PROMPT.format(
        intent=state["intent"],
        sentiment=state["sentiment"],
        rag_context=rag_text,
        user_message=state["user_message"],
    )

    response = llm.invoke(prompt)
    logger.info("Resposta gerada pelo agente")
    return {"response": response.content}
