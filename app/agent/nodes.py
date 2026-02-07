import json
import logging
import re

from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.agent.prompts import CLASSIFY_PROMPT, GENERATE_PROMPT
from app.agent.state import ConversationState
from app.config import settings
from app.models.ong import Ong
from app.rag.retriever import retrieve_similar

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    temperature=settings.OPENAI_TEMPERATURE,
    openai_api_key=settings.OPENAI_API_KEY,
)


def _extract_json(text: str) -> str:
    """Remove markdown code block wrappers if present."""
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text.strip()


def _format_ong(index: int, ong: Ong) -> str:
    """Formata uma ONG em texto legível para o prompt."""
    category = ong.category
    if ong.subcategory:
        category += f"/{ong.subcategory}"

    lines = [f"{index}. {ong.name} ({category}) — {ong.city}/{ong.state}"]

    contact_parts = []
    if ong.website:
        contact_parts.append(f"Site: {ong.website}")
    if ong.phone:
        contact_parts.append(f"Tel: {ong.phone}")
    if ong.email:
        contact_parts.append(f"Email: {ong.email}")
    if contact_parts:
        lines.append("   " + " | ".join(contact_parts))

    if ong.pix_key:
        lines.append(f"   PIX: {ong.pix_key}")
    if ong.bank_info:
        lines.append(f"   Banco: {ong.bank_info}")
    if ong.donation_url:
        lines.append(f"   Doação: {ong.donation_url}")

    return "\n".join(lines)


def classify_node(state: ConversationState) -> dict:
    prompt = CLASSIFY_PROMPT.format(user_message=state["user_message"])
    response = llm.invoke(prompt)

    try:
        raw = _extract_json(response.content)
        classification = json.loads(raw)
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


def make_enrich_node(db: Session):
    """Cria o enrich_node com acesso à sessão do banco via closure."""

    def enrich_node(state: ConversationState) -> dict:
        intent = state["intent"]

        query = db.query(Ong).filter(Ong.is_active.is_(True))

        if intent == "Quero Doar":
            query = query.filter(
                (Ong.pix_key.isnot(None))
                | (Ong.bank_info.isnot(None))
                | (Ong.donation_url.isnot(None))
            )
        elif intent == "Busco Ajuda/Beneficiário":
            query = query.filter(
                Ong.category.in_([
                    "Fome",
                    "Assistência Social",
                    "Saúde",
                    "Saúde Humanitária",
                    "Crianças",
                    "Direitos Humanos",
                    "População de Rua",
                ])
            )

        ongs = query.order_by(Ong.name).limit(10).all()

        if not ongs:
            ong_text = "Nenhuma ONG cadastrada no momento."
        else:
            ong_text = "\n\n".join(
                _format_ong(i + 1, ong) for i, ong in enumerate(ongs)
            )

        logger.info(f"Enrich: {len(ongs)} ONGs selecionadas para intent={intent}")
        return {"ong_context": ong_text}

    return enrich_node


def generate_node(state: ConversationState) -> dict:
    rag_text = "\n\n---\n\n".join(
        item["content"] for item in state["rag_context"]
    )

    prompt = GENERATE_PROMPT.format(
        intent=state["intent"],
        sentiment=state["sentiment"],
        rag_context=rag_text,
        ong_context=state["ong_context"],
        user_message=state["user_message"],
    )

    response = llm.invoke(prompt)
    logger.info("Resposta gerada pelo agente")
    return {"response": response.content}
