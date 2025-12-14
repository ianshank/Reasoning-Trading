"""
Financial Knowledge RAG for document retrieval.

Stores and retrieves financial documents including:
- News articles
- SEC filings
- Analyst reports
- Earnings call transcripts
- Macro economic reports
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.rag.base import (
    BaseRAG,
    DocumentChunk,
    RAGConfig,
    RetrievalResult,
)


class DocumentType(str, Enum):
    """Types of financial documents."""

    NEWS = "news"
    SEC_FILING = "sec_filing"
    ANALYST_REPORT = "analyst_report"
    EARNINGS_CALL = "earnings_call"
    MACRO_REPORT = "macro_report"
    RESEARCH = "research"


class FinancialKnowledgeConfig(BaseSettings):
    """Configuration specific to financial knowledge RAG."""

    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_RAG_",
        case_sensitive=False,
        extra="ignore",
    )

    # Document type settings
    news_max_age_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Maximum age for news articles in days",
    )
    sec_filing_max_age_days: int = Field(
        default=365,
        ge=30,
        le=3650,
        description="Maximum age for SEC filings in days",
    )
    analyst_report_max_age_days: int = Field(
        default=90,
        ge=7,
        le=365,
        description="Maximum age for analyst reports in days",
    )
    earnings_max_age_days: int = Field(
        default=180,
        ge=30,
        le=730,
        description="Maximum age for earnings transcripts in days",
    )
    macro_max_age_days: int = Field(
        default=30,
        ge=7,
        le=180,
        description="Maximum age for macro reports in days",
    )

    # Relevance weights
    recency_weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Weight for document recency in ranking",
    )
    source_quality_weight: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Weight for source quality in ranking",
    )
    semantic_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weight for semantic similarity in ranking",
    )

    # Storage settings
    max_documents_per_type: int = Field(
        default=5000,
        ge=100,
        le=100000,
        description="Maximum documents per type",
    )
    max_chunks_per_document: int = Field(
        default=50,
        ge=5,
        le=500,
        description="Maximum chunks per document",
    )

    # Eviction settings
    eviction_retention_rate: float = Field(
        default=0.8,
        ge=0.5,
        le=0.95,
        description="Fraction of documents to retain during eviction",
    )

    # Source quality scores (0-1)
    default_source_quality: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Default source quality score",
    )


@dataclass
class FinancialDocument:
    """A financial document with metadata."""

    # Identity
    doc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    doc_type: DocumentType = DocumentType.NEWS

    # Content
    title: str = ""
    content: str = ""
    summary: str = ""

    # Source
    source: str = ""
    source_url: str = ""
    source_quality: float = 0.5

    # Associations
    symbols: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)

    # Timestamps
    published_at: datetime = field(default_factory=datetime.now)
    ingested_at: datetime = field(default_factory=datetime.now)

    # Sentiment
    sentiment_score: float = 0.0  # -1 to 1
    sentiment_magnitude: float = 0.0  # 0 to 1

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type.value,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "source": self.source,
            "source_url": self.source_url,
            "source_quality": self.source_quality,
            "symbols": self.symbols,
            "sectors": self.sectors,
            "topics": self.topics,
            "published_at": self.published_at.isoformat(),
            "ingested_at": self.ingested_at.isoformat(),
            "sentiment_score": self.sentiment_score,
            "sentiment_magnitude": self.sentiment_magnitude,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FinancialDocument:
        """Create from dictionary."""
        return cls(
            doc_id=data.get("doc_id", str(uuid.uuid4())),
            doc_type=DocumentType(data.get("doc_type", "news")),
            title=data.get("title", ""),
            content=data.get("content", ""),
            summary=data.get("summary", ""),
            source=data.get("source", ""),
            source_url=data.get("source_url", ""),
            source_quality=data.get("source_quality", 0.5),
            symbols=data.get("symbols", []),
            sectors=data.get("sectors", []),
            topics=data.get("topics", []),
            published_at=datetime.fromisoformat(
                data.get("published_at", datetime.now().isoformat())
            ),
            ingested_at=datetime.fromisoformat(
                data.get("ingested_at", datetime.now().isoformat())
            ),
            sentiment_score=data.get("sentiment_score", 0.0),
            sentiment_magnitude=data.get("sentiment_magnitude", 0.0),
            metadata=data.get("metadata", {}),
        )

    def to_semantic_text(self) -> str:
        """Convert to semantic text for embedding."""
        parts = []

        if self.title:
            parts.append(f"Title: {self.title}")

        if self.summary:
            parts.append(f"Summary: {self.summary}")
        elif self.content:
            # Use first 500 chars of content if no summary
            parts.append(f"Content: {self.content[:500]}")

        if self.symbols:
            parts.append(f"Symbols: {', '.join(self.symbols)}")

        if self.topics:
            parts.append(f"Topics: {', '.join(self.topics)}")

        parts.append(f"Type: {self.doc_type.value}")
        parts.append(f"Source: {self.source}")

        return " | ".join(parts)


class FinancialKnowledgeRAG(BaseRAG[FinancialDocument]):
    """
    RAG system for financial knowledge and documents.

    Stores and retrieves:
    - News articles and market updates
    - SEC filings (10-K, 10-Q, 8-K)
    - Analyst reports and ratings
    - Earnings call transcripts
    - Macro economic reports
    """

    def __init__(
        self,
        rag_config: RAGConfig | None = None,
        knowledge_config: FinancialKnowledgeConfig | None = None,
    ):
        super().__init__(config=rag_config)
        self.knowledge_config = knowledge_config or FinancialKnowledgeConfig()

        # Per-type storage: doc_type -> list of (embedding, doc, chunks)
        self._documents: dict[
            DocumentType,
            list[tuple[NDArray[np.float64], FinancialDocument, list[DocumentChunk]]],
        ] = {dt: [] for dt in DocumentType}

        # Symbol index: symbol -> list of doc_ids
        self._symbol_index: dict[str, list[str]] = {}

    async def _setup_collections(self) -> None:
        """Setup vector database collections."""
        # For ChromaDB backend
        if self.config.vector_db_type.value == "chromadb":
            try:
                import chromadb

                self._client = chromadb.PersistentClient(path=str(self.config.persist_dir))

                # Create collection per document type
                self._collections = {}
                for doc_type in DocumentType:
                    self._collections[doc_type] = self._client.get_or_create_collection(
                        name=f"{self.config.knowledge_collection}_{doc_type.value}",
                        metadata={"hnsw:space": self.config.distance_metric},
                    )
            except ImportError:
                pass  # Fall back to in-memory

    def _get_max_age_days(self, doc_type: DocumentType) -> int:
        """Get maximum age for document type."""
        age_map = {
            DocumentType.NEWS: self.knowledge_config.news_max_age_days,
            DocumentType.SEC_FILING: self.knowledge_config.sec_filing_max_age_days,
            DocumentType.ANALYST_REPORT: self.knowledge_config.analyst_report_max_age_days,
            DocumentType.EARNINGS_CALL: self.knowledge_config.earnings_max_age_days,
            DocumentType.MACRO_REPORT: self.knowledge_config.macro_max_age_days,
            DocumentType.RESEARCH: self.knowledge_config.analyst_report_max_age_days,
        }
        return age_map.get(doc_type, 30)

    def _is_document_expired(self, doc: FinancialDocument) -> bool:
        """Check if document is expired."""
        max_age = self._get_max_age_days(doc.doc_type)
        age = (datetime.now() - doc.published_at).days
        return age > max_age

    async def store(
        self,
        document: FinancialDocument,
        **kwargs,
    ) -> str:
        """
        Store a financial document.

        Args:
            document: Document to store

        Returns:
            Document ID
        """
        # Generate embedding for document
        semantic_text = document.to_semantic_text()
        doc_embedding = self.embedding_provider.encode_single(semantic_text)

        # Chunk the content
        chunks = self._chunk_document(document.content, document.doc_id)

        # Limit chunks
        if len(chunks) > self.knowledge_config.max_chunks_per_document:
            chunks = chunks[: self.knowledge_config.max_chunks_per_document]

        # Generate chunk embeddings
        for chunk in chunks:
            chunk.embedding = self.embedding_provider.encode_single(chunk.content)

        # Store in memory
        doc_type = document.doc_type

        # Check capacity and evict if needed
        if len(self._documents[doc_type]) >= self.knowledge_config.max_documents_per_type:
            await self._evict_documents(doc_type)

        self._documents[doc_type].append((doc_embedding, document, chunks))

        # Update symbol index
        for symbol in document.symbols:
            if symbol not in self._symbol_index:
                self._symbol_index[symbol] = []
            if document.doc_id not in self._symbol_index[symbol]:
                self._symbol_index[symbol].append(document.doc_id)

        return document.doc_id

    async def ingest_document(
        self,
        content: str,
        doc_type: DocumentType | str,
        title: str = "",
        source: str = "",
        symbols: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Ingest a new document into the knowledge base.

        Convenience method for document ingestion.

        Args:
            content: Document content
            doc_type: Type of document
            title: Document title
            source: Source name
            symbols: Associated trading symbols
            metadata: Additional metadata

        Returns:
            Document ID
        """
        if isinstance(doc_type, str):
            doc_type = DocumentType(doc_type)

        document = FinancialDocument(
            doc_type=doc_type,
            title=title,
            content=content,
            source=source,
            symbols=symbols or [],
            source_quality=self.knowledge_config.default_source_quality,
            metadata=metadata or {},
        )

        return await self.store(document)

    async def _evict_documents(self, doc_type: DocumentType) -> None:
        """Evict old documents to make room."""
        docs = self._documents[doc_type]
        if not docs:
            return

        # First remove expired
        docs = [(e, d, c) for e, d, c in docs if not self._is_document_expired(d)]

        # If still over capacity, remove oldest
        if len(docs) >= self.knowledge_config.max_documents_per_type:
            docs.sort(key=lambda x: x[1].ingested_at, reverse=True)
            keep_count = int(len(docs) * self.knowledge_config.eviction_retention_rate)
            docs = docs[:keep_count]

        self._documents[doc_type] = docs

        # Clean up symbol index
        remaining_ids = {d.doc_id for _, d, _ in docs}
        for symbol in list(self._symbol_index.keys()):
            self._symbol_index[symbol] = [
                doc_id for doc_id in self._symbol_index[symbol] if doc_id in remaining_ids
            ]

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        **filters,
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant documents.

        Args:
            query: Query string
            top_k: Number of results
            **filters: symbol, doc_types, date_range filters

        Returns:
            List of retrieval results
        """
        k = top_k or self.config.default_top_k

        # Parse filters
        symbol_filter = filters.get("symbol")
        doc_types = filters.get("doc_types")
        date_range = filters.get("date_range")  # (start_date, end_date)

        if doc_types is None:
            doc_types = list(DocumentType)
        elif isinstance(doc_types, str):
            doc_types = [DocumentType(doc_types)]
        elif isinstance(doc_types, list):
            doc_types = [DocumentType(dt) if isinstance(dt, str) else dt for dt in doc_types]

        # Generate query embedding
        query_embedding = self.embedding_provider.encode_single(query)

        results = []

        for doc_type in doc_types:
            docs = self._documents.get(doc_type, [])

            for doc_embedding, document, chunks in docs:
                # Apply filters
                if symbol_filter and symbol_filter not in document.symbols:
                    continue

                if date_range:
                    start, end = date_range
                    if document.published_at < start or document.published_at > end:
                        continue

                if self._is_document_expired(document):
                    continue

                # Compute document-level similarity
                doc_similarity = self._compute_similarity(query_embedding, doc_embedding)

                # Also check chunk similarities
                best_chunk_similarity = 0.0
                best_chunk = None

                for chunk in chunks:
                    if chunk.embedding is not None:
                        chunk_sim = self._compute_similarity(query_embedding, chunk.embedding)
                        if chunk_sim > best_chunk_similarity:
                            best_chunk_similarity = chunk_sim
                            best_chunk = chunk

                # Combine document and chunk similarity
                combined_similarity = max(doc_similarity, best_chunk_similarity)

                if combined_similarity >= self.config.similarity_threshold:
                    # Compute weighted score
                    recency_score = self._compute_recency_score(document)
                    source_score = document.source_quality

                    weighted_score = (
                        self.knowledge_config.semantic_weight * combined_similarity
                        + self.knowledge_config.recency_weight * recency_score
                        + self.knowledge_config.source_quality_weight * source_score
                    )

                    results.append(
                        RetrievalResult(
                            content=best_chunk.content if best_chunk else document.summary or document.content[:500],
                            chunk=best_chunk,
                            similarity=combined_similarity,
                            doc_id=document.doc_id,
                            doc_type=doc_type.value,
                            metadata=document.to_dict(),
                            score=weighted_score,
                        )
                    )

        # Sort by weighted score
        results.sort(key=lambda x: x.score, reverse=True)

        # Apply ranking
        for i, result in enumerate(results):
            result.rank = i + 1

        return results[:k]

    def _compute_recency_score(self, document: FinancialDocument) -> float:
        """Compute recency score (1.0 for today, decaying over time)."""
        max_age = self._get_max_age_days(document.doc_type)
        age_days = (datetime.now() - document.published_at).days

        if age_days <= 0:
            return 1.0
        elif age_days >= max_age:
            return 0.0
        else:
            # Exponential decay
            return np.exp(-3 * age_days / max_age)

    async def retrieve_for_symbol(
        self,
        symbol: str,
        query: str,
        doc_types: list[DocumentType | str] | None = None,
        top_k: int = 10,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve documents relevant to a specific symbol.

        Convenience method for symbol-based retrieval.

        Args:
            symbol: Trading symbol
            query: Query string
            doc_types: Types of documents to search
            top_k: Number of results
            date_range: Optional date range filter

        Returns:
            List of retrieval results
        """
        return await self.retrieve(
            query,
            top_k=top_k,
            symbol=symbol,
            doc_types=doc_types,
            date_range=date_range,
        )

    async def delete(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        found = False

        for doc_type in DocumentType:
            original_len = len(self._documents[doc_type])
            self._documents[doc_type] = [
                (e, d, c) for e, d, c in self._documents[doc_type] if d.doc_id != doc_id
            ]
            if len(self._documents[doc_type]) < original_len:
                found = True

        # Remove from symbol index
        for symbol in list(self._symbol_index.keys()):
            if doc_id in self._symbol_index[symbol]:
                self._symbol_index[symbol].remove(doc_id)

        return found

    async def get_document_stats(self) -> dict[str, Any]:
        """Get statistics about stored documents."""
        stats = {
            "total_documents": 0,
            "by_type": {},
            "by_symbol": {},
            "total_chunks": 0,
        }

        for doc_type, docs in self._documents.items():
            count = len(docs)
            chunk_count = sum(len(chunks) for _, _, chunks in docs)

            stats["by_type"][doc_type.value] = {
                "count": count,
                "chunks": chunk_count,
            }
            stats["total_documents"] += count
            stats["total_chunks"] += chunk_count

        # Top symbols by document count
        symbol_counts = {
            symbol: len(doc_ids) for symbol, doc_ids in self._symbol_index.items()
        }
        top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        stats["by_symbol"] = dict(top_symbols)

        return stats

    async def get_recent_documents(
        self,
        doc_type: DocumentType | str | None = None,
        limit: int = 10,
    ) -> list[FinancialDocument]:
        """Get most recent documents."""
        if doc_type is not None:
            if isinstance(doc_type, str):
                doc_type = DocumentType(doc_type)
            docs = [d for _, d, _ in self._documents[doc_type]]
        else:
            docs = [d for dt_docs in self._documents.values() for _, d, _ in dt_docs]

        # Sort by published date
        docs.sort(key=lambda x: x.published_at, reverse=True)

        return docs[:limit]

    async def search_by_topic(
        self,
        topic: str,
        top_k: int = 10,
    ) -> list[FinancialDocument]:
        """Search documents by topic."""
        results = []

        for doc_type, docs in self._documents.items():
            for _, document, _ in docs:
                if topic.lower() in [t.lower() for t in document.topics]:
                    results.append(document)

        # Sort by recency
        results.sort(key=lambda x: x.published_at, reverse=True)

        return results[:top_k]
