from unittest.mock import MagicMock, patch

import pytest

import app.rag.retriever as retriever_module


@pytest.fixture(autouse=True)
def reset_vectorstore():
    original = retriever_module._vectorstore
    retriever_module._vectorstore = None
    yield
    retriever_module._vectorstore = original


class TestGetVectorstore:
    @patch("app.rag.retriever._build_vectorstore")
    def test_singleton(self, mock_build):
        mock_vs = MagicMock()
        mock_build.return_value = mock_vs

        vs1 = retriever_module.get_vectorstore()
        vs2 = retriever_module.get_vectorstore()
        assert vs1 is vs2
        mock_build.assert_called_once()


class TestBuildVectorstore:
    @patch("app.rag.retriever.FAISS")
    @patch("app.rag.retriever.OpenAIEmbeddings")
    @patch("app.rag.retriever.load_interactions")
    def test_calls_faiss(self, mock_load, mock_embeddings, mock_faiss):
        mock_docs = [MagicMock()]
        mock_load.return_value = mock_docs
        mock_emb = MagicMock()
        mock_embeddings.return_value = mock_emb

        retriever_module._build_vectorstore()

        mock_faiss.from_documents.assert_called_once_with(mock_docs, mock_emb)


class TestRetrieveSimilar:
    @patch("app.rag.retriever.get_vectorstore")
    def test_returns_formatted_results(self, mock_get_vs):
        doc1 = MagicMock()
        doc1.page_content = "content1"
        doc1.metadata = {"intent": "Quero Doar", "sentiment": "Positivo"}
        doc2 = MagicMock()
        doc2.page_content = "content2"
        doc2.metadata = {"intent": "Voluntariado", "sentiment": "Neutro"}

        mock_vs = MagicMock()
        mock_vs.similarity_search_with_score.return_value = [(doc1, 0.8), (doc2, 0.6)]
        mock_get_vs.return_value = mock_vs

        results = retriever_module.retrieve_similar("query", k=2)
        assert len(results) == 2
        assert results[0]["content"] == "content1"
        assert results[0]["intent"] == "Quero Doar"
        assert results[0]["score"] == 0.8

    @patch("app.rag.retriever.get_vectorstore")
    def test_score_is_float(self, mock_get_vs):
        doc = MagicMock()
        doc.page_content = "content"
        doc.metadata = {"intent": "X", "sentiment": "Y"}
        mock_vs = MagicMock()
        mock_vs.similarity_search_with_score.return_value = [(doc, 0.75)]
        mock_get_vs.return_value = mock_vs

        results = retriever_module.retrieve_similar("q", k=1)
        assert isinstance(results[0]["score"], float)
