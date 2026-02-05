import json
import logging
from pathlib import Path

from langchain.schema import Document

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "BASE_INTERACTION.json"


def load_interactions() -> list[Document]:
    with open(DATA_PATH, encoding="utf-8") as f:
        interactions = json.load(f)

    documents = []
    for item in interactions:
        content = (
            f"Pergunta: {item['user_input']}\n"
            f"Intent: {item['intent']}\n"
            f"Sentimento: {item['sentiment']}\n"
            f"Resposta: {item['ideal_response']}"
        )
        metadata = {
            "intent": item["intent"],
            "sentiment": item["sentiment"],
            "user_input": item["user_input"],
        }
        documents.append(Document(page_content=content, metadata=metadata))

    logger.info(f"{len(documents)} interações carregadas de {DATA_PATH}")
    return documents
