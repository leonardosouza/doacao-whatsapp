from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.graph import build_graph, process_message


class TestBuildGraph:
    def test_compiles(self, db_session):
        graph = build_graph(db_session)
        assert graph is not None


class TestProcessMessage:
    @patch("app.agent.graph.generate_node", return_value={"response": "Olá!"})
    @patch("app.agent.graph.make_enrich_node")
    @patch("app.agent.graph.retrieve_node", return_value={"rag_context": []})
    @patch("app.agent.graph.classify_node", return_value={"intent": "Ambíguo", "sentiment": "Neutro"})
    async def test_end_to_end(self, mock_classify, mock_retrieve, mock_enrich, mock_generate, db_session):
        mock_enrich.return_value = lambda state: {"ong_context": "ONGs aqui"}
        result = await process_message("Oi", db_session)
        assert "response" in result
        assert "intent" in result
        assert "sentiment" in result

    @patch("app.agent.graph.generate_node", return_value={"response": "R"})
    @patch("app.agent.graph.make_enrich_node")
    @patch("app.agent.graph.retrieve_node", return_value={"rag_context": []})
    @patch("app.agent.graph.classify_node", return_value={"intent": "Ambíguo", "sentiment": "Neutro"})
    async def test_initial_state(self, mock_classify, mock_retrieve, mock_enrich, mock_generate, db_session):
        mock_enrich.return_value = lambda state: {"ong_context": ""}
        await process_message("Hello", db_session)
        call_state = mock_classify.call_args[0][0]
        assert call_state["user_message"] == "Hello"
        assert call_state["intent"] == ""
        assert call_state["conversation_history"] == ""
        assert call_state["response"] == ""

    @patch("app.agent.graph.generate_node", return_value={"response": "R"})
    @patch("app.agent.graph.make_enrich_node")
    @patch("app.agent.graph.retrieve_node", return_value={"rag_context": []})
    @patch("app.agent.graph.classify_node", return_value={"intent": "Ambíguo", "sentiment": "Neutro"})
    async def test_passes_conversation_history(self, mock_classify, mock_retrieve, mock_enrich, mock_generate, db_session):
        mock_enrich.return_value = lambda state: {"ong_context": ""}
        history = "Usuário: Oi\nAssistente: Olá"
        await process_message("Hello", db_session, conversation_history=history)
        call_state = mock_classify.call_args[0][0]
        assert call_state["conversation_history"] == history
