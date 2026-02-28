import json
import logging
import re

from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.agent.prompts import (
    CLASSIFY_PROMPT,
    EXTRACT_NAME_PROMPT,
    GENERATE_PROMPT,
    PROFILE_COLLECT_PROMPT,
)
from app.agent.state import ConversationState
from app.config import settings
from app.models.message import Message
from app.models.ong import Ong
from app.rag.retriever import retrieve_similar
from app.services import conversation_service

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


def _bot_asked_for_name(last_bot_content: str | None) -> bool:
    """Verifica se a última mensagem do bot solicitou o nome do usuário."""
    if not last_bot_content:
        return False
    keywords = ["seu nome", "como você se chama", "qual é o seu nome", "qual seu nome"]
    return any(kw in last_bot_content.lower() for kw in keywords)


def _bot_asked_for_email(last_bot_content: str | None) -> bool:
    """Verifica se a última mensagem do bot solicitou o email do usuário."""
    if not last_bot_content:
        return False
    return "email" in last_bot_content.lower() or "e-mail" in last_bot_content.lower()


def _extract_email_from_text(text: str) -> str | None:
    """Extrai endereço de email de um texto via regex."""
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else None


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


def make_profile_node(db: Session, conversation):
    """Cria o profile_node com acesso à conversa via closure.

    Verifica o estágio de coleta de perfil e extrai nome/email da mensagem
    quando o bot havia solicitado essa informação na interação anterior.
    """

    def profile_node(state: ConversationState) -> dict:
        user_name = conversation.user_name
        user_email = conversation.user_email

        last_bot_msg = (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation.id,
                Message.direction == "outbound",
            )
            .order_by(Message.created_at.desc())
            .first()
        )
        last_bot_content = last_bot_msg.content if last_bot_msg else None

        if user_name is None:
            if last_bot_content is None:
                # Primeira interação: nenhuma mensagem anterior do bot → apresentar DoaZap
                profile_stage = "greeting"
            else:
                if _bot_asked_for_name(last_bot_content):
                    prompt = EXTRACT_NAME_PROMPT.format(user_message=state["user_message"])
                    response = llm.invoke(prompt)
                    try:
                        raw = _extract_json(response.content)
                        data = json.loads(raw)
                        if data.get("extracted") and data.get("name"):
                            user_name = data["name"].strip()
                            conversation_service.update_user_profile(db, conversation, user_name=user_name)
                            conversation.user_name = user_name
                    except (json.JSONDecodeError, AttributeError):
                        logger.warning("Falha ao extrair nome do usuário")

                profile_stage = "collecting_name" if user_name is None else (
                    "collecting_email" if user_email is None else "complete"
                )

        elif user_email is None:
            if _bot_asked_for_email(last_bot_content):
                extracted_email = _extract_email_from_text(state["user_message"])
                if extracted_email:
                    conversation_service.update_user_profile(db, conversation, user_email=extracted_email)
                    conversation.user_email = extracted_email
                    user_email = extracted_email

            profile_stage = "complete" if user_email else "collecting_email"

        else:
            profile_stage = "complete"

        logger.info(f"Profile: stage={profile_stage}, name={user_name}, email={user_email}")
        return {
            "user_name": user_name,
            "user_email": user_email,
            "profile_stage": profile_stage,
        }

    return profile_node


def profile_response_node(state: ConversationState) -> dict:
    """Gera a resposta de coleta de perfil (nome ou email)."""
    prompt = PROFILE_COLLECT_PROMPT.format(
        profile_stage=state["profile_stage"],
        user_name=state["user_name"] or "",
        user_message=state["user_message"],
    )
    response = llm.invoke(prompt)
    logger.info(f"Resposta de coleta de perfil gerada (stage={state['profile_stage']})")
    return {"response": response.content, "intent": "Ambíguo", "sentiment": "Neutro"}


def route_profile(state: ConversationState) -> str:
    """Decide o próximo nó com base no estágio de coleta de perfil."""
    if state["profile_stage"] in ("greeting", "collecting_name", "collecting_email"):
        return "profile_response"
    return "classify"


def classify_node(state: ConversationState) -> dict:
    prompt = CLASSIFY_PROMPT.format(
        user_message=state["user_message"],
        conversation_history=state["conversation_history"] or "Nenhum (primeira mensagem)",
    )
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

        if intent == "Fora do Escopo":
            logger.info("Enrich: intent 'Fora do Escopo' — busca de ONGs ignorada")
            return {"ong_context": ""}

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

        limit = 10 if intent in ("Quero Doar", "Busco Ajuda/Beneficiário") else 30
        ongs = query.order_by(Ong.name).limit(limit).all()

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
        conversation_history=state["conversation_history"] or "Nenhum (primeira mensagem)",
        user_message=state["user_message"],
    )

    response = llm.invoke(prompt)
    logger.info("Resposta gerada pelo agente")
    return {"response": response.content}
