"""
RAG/vector_store.py — Self-contained Qdrant Cloud Vector Store
==============================================================
Isolated from ITec-Ai/dapur-ai. Written from scratch for the
Agentic_Rag_Pertamina_camp prototype.

Key design decisions:
  - ingest_bytes() accepts raw bytes (not file path) because Streamlit
    uploads go to memory, not disk.
  - Chunk IDs are deterministic (uuid5) → re-uploading the same file
    replaces its chunks without duplicates (idempotent).
  - Supports multiple Qdrant collections (rks_kb, contract_kb, amendment_kb).
  - HuggingFace embeddings run locally — no API key required.
"""

from __future__ import annotations

import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid5, NAMESPACE_URL

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_community.document_loaders import PyPDFLoader
from langchain_experimental.text_splitter import SemanticChunker
from qdrant_client import QdrantClient, models

load_dotenv()

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Module-level singletons (lazy-initialized, shared across instances)
# ──────────────────────────────────────────────────────────────

_qdrant_client: Optional[QdrantClient] = None
_embeddings: Optional[HuggingFaceEmbeddings] = None


def _get_client() -> QdrantClient:
    """Return a shared Qdrant Cloud client (lazy init)."""
    global _qdrant_client
    if _qdrant_client is None:
        endpoint = os.getenv("QDRANT_CLUSTER_ENDPOINT", "")
        api_key = os.getenv("QDRANT_API_KEY", "")
        if not endpoint:
            raise ValueError(
                "QDRANT_CLUSTER_ENDPOINT is not set. "
                "Please configure your .env file."
            )
        _qdrant_client = QdrantClient(url=endpoint, api_key=api_key)
        logger.info("[VectorStore] Qdrant Cloud client initialized: %s", endpoint)
    return _qdrant_client


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Return shared HuggingFace embeddings (lazy init, runs locally)."""
    global _embeddings
    if _embeddings is None:
        model_name = os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-minilm-l6-v2"
        )
        _embeddings = HuggingFaceEmbeddings(model_name=model_name)
        logger.info("[VectorStore] Embeddings model loaded: %s", model_name)
    return _embeddings


# ──────────────────────────────────────────────────────────────
# Vector dimension constant (must match embedding model output)
# all-minilm-l6-v2 → 384 dims
# ──────────────────────────────────────────────────────────────
VECTOR_SIZE = 384


# ──────────────────────────────────────────────────────────────
# Main class
# ──────────────────────────────────────────────────────────────

class Vector_Store:
    """
    Qdrant Cloud vector store wrapper for the Pertamina AI prototype.

    Usage:
        vs = Vector_Store(collection_name="rks_kb")
        n_chunks = vs.ingest_bytes(pdf_bytes, "my_document.pdf")
        docs = vs.retrieve("spesifikasi teknis perpipaan")
        sources = vs.list_sources()
        vs.delete_source("my_document.pdf")
    """

    def __init__(self, collection_name: str = "rks_kb"):
        self.collection_name = collection_name
        self._ensure_collection()

    # ── Internal helpers ──────────────────────────────────────

    def _ensure_collection(self) -> None:
        """Create the Qdrant collection if it does not yet exist and ensure payload index."""
        client = _get_client()
        if not client.collection_exists(self.collection_name):
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(
                "[VectorStore] Created collection '%s'", self.collection_name
            )

        # Ensure payload index on metadata.source for idempotent delete & filtering
        try:
            client.create_payload_index(
                collection_name=self.collection_name,
                field_name="metadata.source",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass  # Index already exists or already created

    @property
    def _doc_store(self) -> QdrantVectorStore:
        return QdrantVectorStore(
            client=_get_client(),
            collection_name=self.collection_name,
            embedding=_get_embeddings(),
        )

    # ── Public API ────────────────────────────────────────────

    def ingest_bytes(self, file_bytes: bytes, filename: str) -> int:
        """
        Ingest a PDF from raw bytes (e.g., from a Streamlit file_uploader).

        The file is temporarily written to disk so PyPDFLoader can parse it,
        then immediately deleted. Chunk IDs are deterministic, so re-uploading
        the same filename replaces its chunks without creating duplicates.

        Args:
            file_bytes: Raw PDF content as bytes.
            filename:   Original filename (used as source metadata + ID seed).

        Returns:
            Number of chunks ingested.

        Raises:
            ValueError: If no extractable text is found (e.g. scanned PDF).
        """
        # Write to a temp file (PyPDFLoader requires a path)
        suffix = Path(filename).suffix or ".pdf"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            loaded = PyPDFLoader(tmp_path).load()
        finally:
            os.unlink(tmp_path)  # always clean up

        # Normalize source metadata to just the filename (no container paths)
        source = Path(filename).name
        for doc in loaded:
            doc.metadata["source"] = source

        # Semantic chunking using the same embedding model
        splitter = SemanticChunker(_get_embeddings())
        chunks: List[Document] = splitter.split_documents(loaded)
        chunks = [
            c for c in chunks
            if c.page_content and isinstance(c.page_content, str) and c.page_content.strip()
        ]

        if not chunks:
            raise ValueError(
                f"Tidak ada teks yang bisa diekstrak dari '{filename}'. "
                "Pastikan file bukan PDF hasil scan (gambar)."
            )

        # Deterministic IDs → idempotent ingest
        ids = [
            str(uuid5(NAMESPACE_URL, f"{self.collection_name}::{source}::{i}"))
            for i in range(len(chunks))
        ]

        # Remove stale chunks from a previous version of this file
        self.delete_source(source)

        self._doc_store.add_documents(documents=chunks, ids=ids)
        logger.info(
            "[VectorStore] Ingested '%s' → %d chunks into '%s'",
            source, len(chunks), self.collection_name,
        )
        return len(chunks)

    def ingest_file(self, file_path: str) -> int:
        """
        Convenience method: ingest a PDF from a local file path.
        Internally reads the file and delegates to ingest_bytes().
        """
        path = Path(file_path)
        return self.ingest_bytes(path.read_bytes(), path.name)

    def list_sources(self) -> Dict[str, int]:
        """
        List all ingested documents in this collection.

        Returns:
            Dict mapping filename → chunk count.
            e.g. {"RKS_Perpipaan.pdf": 42, "BOQ_2025.pdf": 18}
        """
        client = _get_client()
        counts: Dict[str, int] = {}
        offset = None

        while True:
            points, offset = client.scroll(
                collection_name=self.collection_name,
                limit=256,
                offset=offset,
                with_payload=["metadata"],
                with_vectors=False,
            )
            for point in points:
                src = (
                    (point.payload or {})
                    .get("metadata", {})
                    .get("source", "unknown")
                )
                src = os.path.basename(str(src))
                counts[src] = counts.get(src, 0) + 1

            if offset is None:
                break

        return counts

    def delete_source(self, filename: str) -> None:
        """
        Remove all chunks belonging to a specific document.

        Args:
            filename: The original filename (as stored in metadata.source).
        """
        source = os.path.basename(filename)
        _get_client().delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.source",
                            match=models.MatchValue(value=source),
                        )
                    ]
                )
            ),
        )
        logger.info(
            "[VectorStore] Deleted chunks for '%s' from '%s'",
            source, self.collection_name,
        )

    def retrieve(self, query: str, k: int = 4) -> List[Document]:
        """
        Perform a similarity search against this collection.

        Args:
            query: Natural language query string.
            k:     Number of top results to return (default: 4).

        Returns:
            List of LangChain Document objects.
        """
        return self._doc_store.similarity_search(query, k=k)

    def as_retriever(self, k: int = 4):
        """Return a LangChain-compatible retriever (for use in chains/agents)."""
        return self._doc_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k},
        )

    # ── Legacy compatibility (used by existing agent.py / tools.py) ──

    @property
    def doc_store(self) -> QdrantVectorStore:
        """Expose doc_store directly for backward compatibility with agent.py."""
        return self._doc_store
