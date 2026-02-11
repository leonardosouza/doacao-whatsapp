from unittest.mock import MagicMock, patch

import pytest

from app.agent.nodes import (
    _extract_json,
    _format_ong,
    classify_node,
    generate_node,
    make_enrich_node,
    retrieve_node,
)
from app.models.ong import Ong


# ── _extract_json ────────────────────────────────────────────────────
class TestExtractJson:
    def test_raw_json(self):
        raw = '{"intent":"Quero Doar","sentiment":"Positivo"}'
        assert _extract_json(raw) == raw

    def test_markdown_block(self):
        text = '```json\n{"intent":"Quero Doar"}\n```'
        assert _extract_json(text) == '{"intent":"Quero Doar"}'

    def test_without_lang_hint(self):
        text = '```\n{"intent":"Quero Doar"}\n```'
        assert _extract_json(text) == '{"intent":"Quero Doar"}'

    def test_surrounding_text(self):
        text = 'Sure, here is: ```json\n{"intent":"X"}\n``` done'
        assert _extract_json(text) == '{"intent":"X"}'


# ── _format_ong ──────────────────────────────────────────────────────
class TestFormatOng:
    def _make_ong(self, **kwargs):
        defaults = {
            "name": "ONG Teste",
            "category": "Saúde",
            "subcategory": None,
            "city": "São Paulo",
            "state": "SP",
            "website": None,
            "phone": None,
            "email": None,
            "pix_key": None,
            "bank_info": None,
            "donation_url": None,
        }
        defaults.update(kwargs)
        mock = MagicMock(spec=Ong)
        for k, v in defaults.items():
            setattr(mock, k, v)
        return mock

    def test_full_data(self):
        ong = self._make_ong(
            website="https://ong.org",
            phone="(11) 1234-5678",
            email="a@b.com",
            pix_key="pix@ong.org",
            bank_info="Banco X Ag 001",
            donation_url="https://doe.org",
        )
        result = _format_ong(1, ong)
        assert "1. ONG Teste (Saúde)" in result
        assert "Site: https://ong.org" in result
        assert "Tel: (11) 1234-5678" in result
        assert "Email: a@b.com" in result
        assert "PIX: pix@ong.org" in result
        assert "Banco: Banco X Ag 001" in result
        assert "Doação: https://doe.org" in result

    def test_minimal_data(self):
        ong = self._make_ong()
        result = _format_ong(1, ong)
        assert "1. ONG Teste (Saúde) — São Paulo/SP" == result

    def test_subcategory(self):
        ong = self._make_ong(subcategory="Infantil")
        result = _format_ong(1, ong)
        assert "(Saúde/Infantil)" in result


# ── classify_node ────────────────────────────────────────────────────
class TestClassifyNode:
    @patch("app.agent.nodes.llm")
    def test_valid_json(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(
            content='{"intent":"Quero Doar","sentiment":"Positivo"}'
        )
        state = {"user_message": "Quero doar", "conversation_history": "", "intent": "", "sentiment": "", "rag_context": [], "ong_context": "", "response": ""}
        result = classify_node(state)
        assert result["intent"] == "Quero Doar"
        assert result["sentiment"] == "Positivo"

    @patch("app.agent.nodes.llm")
    def test_malformed_json_fallback(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="I don't understand")
        state = {"user_message": "xyz", "conversation_history": "", "intent": "", "sentiment": "", "rag_context": [], "ong_context": "", "response": ""}
        result = classify_node(state)
        assert result["intent"] == "Ambíguo"
        assert result["sentiment"] == "Neutro"

    @patch("app.agent.nodes.llm")
    def test_markdown_block(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(
            content='```json\n{"intent":"Voluntariado","sentiment":"Neutro"}\n```'
        )
        state = {"user_message": "Quero ser voluntário", "conversation_history": "", "intent": "", "sentiment": "", "rag_context": [], "ong_context": "", "response": ""}
        result = classify_node(state)
        assert result["intent"] == "Voluntariado"


# ── retrieve_node ────────────────────────────────────────────────────
class TestRetrieveNode:
    @patch("app.agent.nodes.retrieve_similar")
    def test_returns_rag_results(self, mock_retrieve):
        mock_data = [
            {"content": "doc1", "intent": "Quero Doar", "sentiment": "Positivo", "score": 0.8},
            {"content": "doc2", "intent": "Voluntariado", "sentiment": "Neutro", "score": 0.6},
        ]
        mock_retrieve.return_value = mock_data
        state = {"user_message": "Quero doar", "conversation_history": "", "intent": "", "sentiment": "", "rag_context": [], "ong_context": "", "response": ""}
        result = retrieve_node(state)
        assert result["rag_context"] == mock_data
        mock_retrieve.assert_called_once_with("Quero doar", k=3)


# ── enrich_node ──────────────────────────────────────────────────────
class TestEnrichNode:
    def test_quero_doar_filters_payment(self, db_session, multiple_ongs_in_db):
        enrich = make_enrich_node(db_session)
        state = {"user_message": "", "conversation_history": "", "intent": "Quero Doar", "sentiment": "", "rag_context": [], "ong_context": "", "response": ""}
        result = enrich(state)
        # Only ONGs with pix_key, bank_info, or donation_url should appear
        assert "ONG Fome A" in result["ong_context"]  # has pix_key
        assert "ONG Saúde B" in result["ong_context"]  # has bank_info
        assert "ONG Crianças E" in result["ong_context"]  # has donation_url
        assert "ONG Animais C" not in result["ong_context"]  # no payment info
        assert "ONG Inativa F" not in result["ong_context"]  # inactive

    def test_busco_ajuda_filters_social(self, db_session, multiple_ongs_in_db):
        enrich = make_enrich_node(db_session)
        state = {"user_message": "", "conversation_history": "", "intent": "Busco Ajuda/Beneficiário", "sentiment": "", "rag_context": [], "ong_context": "", "response": ""}
        result = enrich(state)
        assert "ONG Fome A" in result["ong_context"]  # category "Fome"
        assert "ONG Saúde B" in result["ong_context"]  # category "Saúde"
        assert "ONG Assistência D" in result["ong_context"]  # category "Assistência Social"
        assert "ONG Crianças E" in result["ong_context"]  # category "Crianças"
        assert "ONG Animais C" not in result["ong_context"]  # "Animais" not in list

    def test_ambiguo_returns_all_active(self, db_session, multiple_ongs_in_db):
        enrich = make_enrich_node(db_session)
        state = {"user_message": "", "conversation_history": "", "intent": "Ambíguo", "sentiment": "", "rag_context": [], "ong_context": "", "response": ""}
        result = enrich(state)
        assert "ONG Fome A" in result["ong_context"]
        assert "ONG Animais C" in result["ong_context"]
        assert "ONG Inativa F" not in result["ong_context"]

    def test_empty_db_placeholder(self, db_session):
        enrich = make_enrich_node(db_session)
        state = {"user_message": "", "conversation_history": "", "intent": "Quero Doar", "sentiment": "", "rag_context": [], "ong_context": "", "response": ""}
        result = enrich(state)
        assert result["ong_context"] == "Nenhuma ONG cadastrada no momento."


# ── generate_node ────────────────────────────────────────────────────
class TestGenerateNode:
    @patch("app.agent.nodes.llm")
    def test_passes_context(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="Resposta gerada")
        state = {
            "user_message": "Quero doar",
            "conversation_history": "",
            "intent": "Quero Doar",
            "sentiment": "Positivo",
            "rag_context": [{"content": "doc1"}, {"content": "doc2"}],
            "ong_context": "1. ONG Teste",
            "response": "",
        }
        result = generate_node(state)
        assert result["response"] == "Resposta gerada"
        call_args = mock_llm.invoke.call_args[0][0]
        assert "Quero Doar" in call_args
        assert "Positivo" in call_args
        assert "doc1" in call_args
        assert "1. ONG Teste" in call_args


# ── classify_node com histórico ─────────────────────────────────────
class TestClassifyNodeWithHistory:
    @patch("app.agent.nodes.llm")
    def test_history_included_in_prompt(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(
            content='{"intent":"Quero Doar","sentiment":"Positivo"}'
        )
        state = {
            "user_message": "Qual o PIX?",
            "conversation_history": "Usuário: Quero doar para animais\nAssistente: Temos várias ONGs...",
            "intent": "", "sentiment": "", "rag_context": [], "ong_context": "", "response": "",
        }
        classify_node(state)
        call_args = mock_llm.invoke.call_args[0][0]
        assert "Quero doar para animais" in call_args
        assert "Qual o PIX?" in call_args

    @patch("app.agent.nodes.llm")
    def test_empty_history_shows_fallback(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(
            content='{"intent":"Ambíguo","sentiment":"Neutro"}'
        )
        state = {
            "user_message": "Oi",
            "conversation_history": "",
            "intent": "", "sentiment": "", "rag_context": [], "ong_context": "", "response": "",
        }
        classify_node(state)
        call_args = mock_llm.invoke.call_args[0][0]
        assert "Nenhum (primeira mensagem)" in call_args


# ── generate_node com histórico ─────────────────────────────────────
class TestGenerateNodeWithHistory:
    @patch("app.agent.nodes.llm")
    def test_history_included_in_prompt(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="Resposta contextual")
        state = {
            "user_message": "Qual o PIX?",
            "conversation_history": "Usuário: Quero doar para animais\nAssistente: Temos a ONG Animais C...",
            "intent": "Quero Doar", "sentiment": "Positivo",
            "rag_context": [{"content": "doc1"}], "ong_context": "ONGs aqui", "response": "",
        }
        generate_node(state)
        call_args = mock_llm.invoke.call_args[0][0]
        assert "Quero doar para animais" in call_args

    @patch("app.agent.nodes.llm")
    def test_empty_history_shows_fallback(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="Resposta")
        state = {
            "user_message": "Oi",
            "conversation_history": "",
            "intent": "Ambíguo", "sentiment": "Neutro",
            "rag_context": [], "ong_context": "", "response": "",
        }
        generate_node(state)
        call_args = mock_llm.invoke.call_args[0][0]
        assert "Nenhum (primeira mensagem)" in call_args
