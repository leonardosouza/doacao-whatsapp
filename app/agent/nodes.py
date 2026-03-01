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

MAX_PROFILE_RETRIES = 3  # tentativas máximas de coleta de nome antes de prosseguir sem ele

_ESTADOS_BR = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
    "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
    "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}

_CITY_TO_STATE: dict[str, str] = {
    "são paulo": "SP", "campinas": "SP", "santos": "SP", "sorocaba": "SP",
    "ribeirão preto": "SP", "osasco": "SP", "piracicaba": "SP", "guarulhos": "SP",
    "rio de janeiro": "RJ", "niterói": "RJ", "petrópolis": "RJ",
    "belo horizonte": "MG", "uberlândia": "MG", "contagem": "MG",
    "salvador": "BA", "feira de santana": "BA",
    "fortaleza": "CE", "caucaia": "CE",
    "recife": "PE", "olinda": "PE", "caruaru": "PE",
    "manaus": "AM",
    "porto alegre": "RS", "caxias do sul": "RS",
    "curitiba": "PR", "londrina": "PR", "maringá": "PR",
    "brasília": "DF",
    "belém": "PA",
    "goiânia": "GO",
    "florianópolis": "SC", "joinville": "SC", "blumenau": "SC",
    "natal": "RN",
    "maceió": "AL",
    "aracaju": "SE",
    "joão pessoa": "PB",
    "macapá": "AP",
    "porto velho": "RO",
    "boa vista": "RR",
    "palmas": "TO",
    "são luís": "MA",
    "teresina": "PI",
    "campo grande": "MS",
    "cuiabá": "MT",
    "vitória": "ES",
    "rio branco": "AC",
}

_KEYWORD_CATEGORY_MAP: dict[str, str] = {
    "lgbt": "LGBTQIA+",
    "lgbtqia": "LGBTQIA+",
    "gay": "LGBTQIA+",
    "lésbica": "LGBTQIA+",
    "lesbica": "LGBTQIA+",
    "trans ": "LGBTQIA+",
    "transgênero": "LGBTQIA+",
    "transgenero": "LGBTQIA+",
    "meio ambiente": "Meio Ambiente",
    "ambiental": "Meio Ambiente",
    "ecologia": "Meio Ambiente",
    "ecológic": "Meio Ambiente",
    "sustentabilidade": "Meio Ambiente",
    "animal": "Animais",
    "pets": "Animais",
    "criança": "Educação",
    "criancas": "Educação",
    "educação": "Educação",
    "educacao": "Educação",
    "escola": "Educação",
    "fome": "Fome",
    "alimento": "Fome",
    "alimentação": "Fome",
    "alimentacao": "Fome",
    "comida": "Fome",
    "mulher": "Mulheres",
    "mulheres": "Mulheres",
    "feminino": "Mulheres",
    "feminism": "Mulheres",
    "saúde": "Saúde",
    "saude": "Saúde",
    "deficiência": "Pessoas com Deficiência",
    "deficiencia": "Pessoas com Deficiência",
    "autismo": "Pessoas com Deficiência",
    "cultura": "Cultura",
    "arte": "Cultura",
    "teatro": "Cultura",
    "música": "Cultura",
    "musica": "Cultura",
    "direitos humanos": "Direitos Humanos",
    "assistência social": "Assistência Social",
    "assistencia social": "Assistência Social",
    "refugiad": "Direitos Humanos",
    "indígena": "Direitos Humanos",
    "indigena": "Direitos Humanos",
    "negro": "Direitos Humanos",
    "negros": "Direitos Humanos",
    "racial": "Direitos Humanos",
}


def _extract_state_from_text(text: str) -> str | None:
    """Extrai UF do texto: primeiro tenta sigla explícita, depois nome de cidade."""
    normalized = text.upper()
    # 1. Sigla de 2 letras precedida de "em", "no", "na", "de" ou após vírgula/ponto
    for match in re.finditer(r"\b([A-Z]{2})\b", normalized):
        if match.group(1) in _ESTADOS_BR:
            return match.group(1)
    # 2. Nome de cidade → estado
    lower = text.lower()
    for city, state in _CITY_TO_STATE.items():
        if city in lower:
            return state
    return None


def _extract_category_hint(text: str) -> str | None:
    """Mapeia palavras-chave da mensagem para uma categoria de ONG."""
    lower = text.lower()
    for keyword, category in _KEYWORD_CATEGORY_MAP.items():
        if keyword in lower:
            return category
    return None

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

    return "\n".join(lines)


def make_profile_node(db: Session, conversation):
    """Cria o profile_node com acesso à conversa via closure.

    Verifica o estágio de coleta de perfil e extrai o nome da mensagem
    quando o bot havia solicitado essa informação na interação anterior.
    """

    def profile_node(state: ConversationState) -> dict:
        user_name = conversation.user_name

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

        retries = state.get("profile_retries", 0)

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

                if user_name is None:
                    retries += 1
                    if retries >= MAX_PROFILE_RETRIES:
                        # Esgotou tentativas: prossegue sem nome para não entrar em loop
                        profile_stage = "complete"
                        logger.warning(
                            f"Limite de tentativas de coleta de nome atingido "
                            f"(conv={conversation.id}, retries={retries})"
                        )
                    else:
                        profile_stage = "collecting_name"
                else:
                    profile_stage = "complete"

        else:
            profile_stage = "complete"

        logger.info(f"Profile: stage={profile_stage}, name={user_name}, retries={retries}")
        return {
            "user_name": user_name,
            "profile_stage": profile_stage,
            "profile_retries": retries,
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
    if state["profile_stage"] in ("greeting", "collecting_name"):
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
        user_message = state["user_message"]

        if intent == "Fora do Escopo":
            logger.info("Enrich: intent 'Fora do Escopo' — busca de ONGs ignorada")
            return {"ong_context": ""}

        query = db.query(Ong).filter(Ong.is_active.is_(True))
        applied_hint = False

        if intent == "Quero Doar":
            query = query.filter(
                (Ong.pix_key.isnot(None))
                | (Ong.bank_info.isnot(None))
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
        else:
            # Para intents sem filtro rígido (Informação Geral, Voluntariado,
            # Parceria, Ambíguo): tenta filtrar por categoria e/ou estado
            # extraídos da mensagem do usuário para reduzir o contexto enviado ao LLM.
            category_hint = _extract_category_hint(user_message)
            if category_hint and intent == "Informação Geral":
                query = query.filter(Ong.category == category_hint)
                applied_hint = True
                logger.info(f"Enrich: categoria inferida='{category_hint}'")

            state_hint = _extract_state_from_text(user_message)
            if state_hint:
                query = query.filter(Ong.state == state_hint)
                applied_hint = True
                logger.info(f"Enrich: estado inferido='{state_hint}'")

        if intent in ("Quero Doar", "Busco Ajuda/Beneficiário"):
            limit = 10
        elif applied_hint:
            limit = 15
        else:
            limit = 30
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
