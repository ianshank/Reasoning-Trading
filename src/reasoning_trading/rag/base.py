"""
Base abstractions for RAG (Retrieval-Augmented Generation) systems.

Provides configurable, extensible base classes for vector database
backed retrieval systems with no hardcoded values.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Type variable for document content
T = TypeVar("T")


class EmbeddingModelType(str, Enum):
    """Supported embedding model types."""

    MINILM_L6 = "all-MiniLM-L6-v2"
    MPNET_BASE = "all-mpnet-base-v2"
    BGE_SMALL = "BAAI/bge-small-en-v1.5"
    BGE_BASE = "BAAI/bge-base-en-v1.5"
    CUSTOM = "custom"


class VectorDBType(str, Enum):
    """Supported vector database backends."""

    CHROMADB = "chromadb"
    FAISS = "faiss"
    IN_MEMORY = "in_memory"


class RAGConfig(BaseSettings):
    """
    Configuration for RAG systems.

    All values are configurable via environment variables with RAG_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        case_sensitive=False,
        extra="ignore",
    )

    # Storage settings
    persist_dir: Path = Field(
        default=Path("./data/rag_db"),
        description="Directory for persisting vector databases",
    )
    vector_db_type: VectorDBType = Field(
        default=VectorDBType.CHROMADB,
        description="Vector database backend type",
    )

    # Embedding settings
    embedding_model: EmbeddingModelType = Field(
        default=EmbeddingModelType.MINILM_L6,
        description="Embedding model to use",
    )
    embedding_dimension: int = Field(
        default=384,
        ge=64,
        le=4096,
        description="Embedding vector dimension",
    )
    custom_embedding_model_path: str | None = Field(
        default=None,
        description="Path to custom embedding model",
    )

    # Retrieval settings
    default_top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Default number of results to retrieve",
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for retrieval",
    )
    distance_metric: str = Field(
        default="cosine",
        description="Distance metric (cosine, l2, ip)",
    )

    # Chunking settings
    chunk_size: int = Field(
        default=512,
        ge=64,
        le=4096,
        description="Document chunk size in tokens",
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=256,
        description="Overlap between chunks",
    )

    # Performance settings
    batch_size: int = Field(
        default=32,
        ge=1,
        le=256,
        description="Batch size for embedding operations",
    )
    max_concurrent_queries: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum concurrent query operations",
    )

    # TTL settings
    default_ttl_hours: int = Field(
        default=168,  # 1 week
        ge=1,
        le=8760,  # 1 year
        description="Default TTL for stored documents in hours",
    )

    # Collection names
    patterns_collection: str = Field(
        default="trading_patterns",
        description="Collection name for trading patterns",
    )
    knowledge_collection: str = Field(
        default="financial_knowledge",
        description="Collection name for financial knowledge",
    )
    strategies_collection: str = Field(
        default="mcts_strategies",
        description="Collection name for MCTS strategies",
    )


@dataclass
class DocumentChunk:
    """A chunk of a document with metadata."""

    content: str
    chunk_index: int
    doc_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: NDArray[np.float64] | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "doc_id": self.doc_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentChunk:
        """Create from dictionary."""
        return cls(
            content=data["content"],
            chunk_index=data["chunk_index"],
            doc_id=data["doc_id"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
        )


@dataclass
class RetrievalResult:
    """Result from a RAG retrieval query."""

    # Retrieved content
    content: str
    chunk: DocumentChunk | None = None

    # Similarity metrics
    similarity: float = 0.0
    distance: float = 0.0

    # Source metadata
    doc_id: str = ""
    doc_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # Ranking info
    rank: int = 0
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "similarity": self.similarity,
            "distance": self.distance,
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "metadata": self.metadata,
            "rank": self.rank,
            "score": self.score,
        }


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    def encode(self, texts: list[str]) -> NDArray[np.float64]:
        """Encode texts to embeddings."""
        ...

    def encode_single(self, text: str) -> NDArray[np.float64]:
        """Encode a single text to embedding."""
        ...

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        ...


class DefaultEmbeddingProvider:
    """
    Default embedding provider using sentence-transformers.

    Lazily loads the model on first use for efficiency.
    """

    def __init__(self, config: RAGConfig):
        self.config = config
        self._model = None
        self._dimension = config.embedding_dimension

    @property
    def model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                model_name = (
                    self.config.custom_embedding_model_path
                    if self.config.embedding_model == EmbeddingModelType.CUSTOM
                    else self.config.embedding_model.value
                )
                self._model = SentenceTransformer(model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for embeddings. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    def encode(self, texts: list[str]) -> NDArray[np.float64]:
        """Encode texts to embeddings."""
        if not texts:
            return np.array([], dtype=np.float64)
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.astype(np.float64)

    def encode_single(self, text: str) -> NDArray[np.float64]:
        """Encode a single text to embedding."""
        return self.encode([text])[0]

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension


class BaseRAG(ABC, Generic[T]):
    """
    Abstract base class for RAG implementations.

    Provides common functionality for:
    - Document storage and retrieval
    - Embedding management
    - Collection lifecycle
    """

    def __init__(
        self,
        config: RAGConfig | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.config = config or RAGConfig()
        self._embedding_provider = embedding_provider
        self._initialized = False

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        """Get or create embedding provider."""
        if self._embedding_provider is None:
            self._embedding_provider = DefaultEmbeddingProvider(self.config)
        return self._embedding_provider

    @abstractmethod
    async def store(self, document: T, **kwargs) -> str:
        """
        Store a document in the RAG system.

        Args:
            document: Document to store
            **kwargs: Additional storage parameters

        Returns:
            Document ID
        """
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        **filters,
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Query string
            top_k: Number of results to return
            **filters: Additional filter criteria

        Returns:
            List of retrieval results
        """
        pass

    @abstractmethod
    async def delete(self, doc_id: str) -> bool:
        """
        Delete a document from the RAG system.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if deleted successfully
        """
        pass

    async def initialize(self) -> None:
        """Initialize the RAG system."""
        if self._initialized:
            return

        # Ensure persist directory exists
        self.config.persist_dir.mkdir(parents=True, exist_ok=True)

        await self._setup_collections()
        self._initialized = True

    @abstractmethod
    async def _setup_collections(self) -> None:
        """Setup vector database collections."""
        pass

    def _chunk_document(self, content: str, doc_id: str) -> list[DocumentChunk]:
        """
        Chunk a document into smaller pieces.

        Args:
            content: Document content
            doc_id: Document identifier

        Returns:
            List of document chunks
        """
        if not content:
            return []

        chunks = []
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap

        # Simple character-based chunking
        # In production, use token-based chunking
        start = 0
        chunk_idx = 0

        while start < len(content):
            end = min(start + chunk_size, len(content))

            # Try to break at sentence boundary
            if end < len(content):
                # Look for sentence endings
                for sep in [". ", ".\n", "! ", "!\n", "? ", "?\n"]:
                    last_sep = content[start:end].rfind(sep)
                    if last_sep > chunk_size // 2:
                        end = start + last_sep + len(sep)
                        break

            chunk_content = content[start:end].strip()
            if chunk_content:
                chunks.append(
                    DocumentChunk(
                        content=chunk_content,
                        chunk_index=chunk_idx,
                        doc_id=doc_id,
                    )
                )
                chunk_idx += 1

            start = end - overlap if end < len(content) else end

        return chunks

    def _compute_similarity(
        self,
        query_embedding: NDArray[np.float64],
        doc_embedding: NDArray[np.float64],
    ) -> float:
        """Compute similarity between embeddings."""
        if self.config.distance_metric == "cosine":
            # Cosine similarity
            norm_q = np.linalg.norm(query_embedding)
            norm_d = np.linalg.norm(doc_embedding)
            if norm_q == 0 or norm_d == 0:
                return 0.0
            return float(np.dot(query_embedding, doc_embedding) / (norm_q * norm_d))
        elif self.config.distance_metric == "l2":
            # L2 distance converted to similarity
            distance = np.linalg.norm(query_embedding - doc_embedding)
            return float(1.0 / (1.0 + distance))
        elif self.config.distance_metric == "ip":
            # Inner product (dot product)
            return float(np.dot(query_embedding, doc_embedding))
        else:
            # Default to cosine
            norm_q = np.linalg.norm(query_embedding)
            norm_d = np.linalg.norm(doc_embedding)
            if norm_q == 0 or norm_d == 0:
                return 0.0
            return float(np.dot(query_embedding, doc_embedding) / (norm_q * norm_d))

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about the RAG system."""
        return {
            "initialized": self._initialized,
            "config": {
                "persist_dir": str(self.config.persist_dir),
                "vector_db_type": self.config.vector_db_type.value,
                "embedding_model": self.config.embedding_model.value,
                "embedding_dimension": self.config.embedding_dimension,
            },
        }
