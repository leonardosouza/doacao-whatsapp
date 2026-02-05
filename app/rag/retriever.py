import logging

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from app.config import settings
from app.rag.loader import load_interactions

logger = logging.getLogger(__name__)

_vectorstore: FAISS | None = None


def get_vectorstore() -> FAISS:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = _build_vectorstore()
    return _vectorstore


def _build_vectorstore() -> FAISS:
    documents = load_interactions()
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.OPENAI_API_KEY,
    )
    vectorstore = FAISS.from_documents(documents, embeddings)
    logger.info("Vectorstore FAISS criado com sucesso")
    return vectorstore


def retrieve_similar(query: str, k: int = 3) -> list[dict]:
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_score(query, k=k)

    retrieved = []
    for doc, score in results:
        retrieved.append(
            {
                "content": doc.page_content,
                "intent": doc.metadata.get("intent"),
                "sentiment": doc.metadata.get("sentiment"),
                "score": float(score),
            }
        )

    logger.info(f"RAG: {len(retrieved)} documentos recuperados para: '{query[:50]}...'")
    return retrieved
