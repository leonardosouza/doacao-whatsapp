from langchain.schema import Document

from app.rag.loader import load_interactions


class TestLoadInteractions:
    def test_returns_documents(self):
        docs = load_interactions()
        assert len(docs) > 0
        assert all(isinstance(d, Document) for d in docs)

    def test_document_content_format(self):
        docs = load_interactions()
        doc = docs[0]
        assert "Pergunta:" in doc.page_content
        assert "Intent:" in doc.page_content
        assert "Sentimento:" in doc.page_content
        assert "Resposta:" in doc.page_content

    def test_document_metadata(self):
        docs = load_interactions()
        doc = docs[0]
        assert "intent" in doc.metadata
        assert "sentiment" in doc.metadata
        assert "user_input" in doc.metadata
