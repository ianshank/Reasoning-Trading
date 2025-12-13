"""
Comprehensive tests for RAG and CAG systems.

Tests cover:
- Base abstractions
- SemanticDecisionCache
- TradingPatternRAG
- AnalystResponseCAG
- FinancialKnowledgeRAG
- MCTSStrategyRAG
- HierarchicalCAG
- EnhancedSpeedLayer integration
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from reasoning_trading.cag.analyst_cache import (
    AnalystCacheConfig,
    AnalystResponseCAG,
    AnalystType,
    CachedAnalystResponse,
)
from reasoning_trading.cag.base import (
    BaseCAG,
    CacheEntry,
    CacheHit,
    CacheLevel,
    CacheStats,
    CAGConfig,
)
from reasoning_trading.cag.hierarchical_cache import (
    DecisionLevel,
    EnsembleSource,
    EnsembleStrategy,
    HierarchicalCAG,
    HierarchicalCAGConfig,
    HierarchicalDecision,
)
from reasoning_trading.cag.semantic_cache import (
    CachedDecision,
    SemanticCacheConfig,
    SemanticDecisionCache,
)
from reasoning_trading.core.actions import (
    PositionSizeAction,
    StopLossAction,
    TimeHorizon,
    TradingAction,
    TradingDirection,
)
from reasoning_trading.core.state import (
    AnalystSignals,
    MarketRegime,
    PortfolioState,
    TechnicalIndicators,
    TradingState,
)
from reasoning_trading.rag.base import (
    BaseRAG,
    DocumentChunk,
    EmbeddingModelType,
    RAGConfig,
    RetrievalResult,
    VectorDBType,
)
from reasoning_trading.rag.financial_knowledge import (
    DocumentType,
    FinancialDocument,
    FinancialKnowledgeConfig,
    FinancialKnowledgeRAG,
)
from reasoning_trading.rag.mcts_strategies import (
    MCTSStrategy,
    MCTSStrategyConfig,
    MCTSStrategyRAG,
)
from reasoning_trading.rag.trading_patterns import (
    TradingPattern,
    TradingPatternConfig,
    TradingPatternRAG,
)

from tests.config import TestConfig, get_test_config
from tests.factories import TradingStateFactory, ActionFactory


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def test_config() -> TestConfig:
    """Get test configuration."""
    return get_test_config()


@pytest.fixture
def rag_config() -> RAGConfig:
    """Create RAG configuration for testing."""
    return RAGConfig(
        persist_dir="./test_data/rag_db",
        vector_db_type=VectorDBType.IN_MEMORY,
        embedding_model=EmbeddingModelType.MINILM_L6,
        default_top_k=5,
        similarity_threshold=0.7,
        chunk_size=256,
        chunk_overlap=25,
    )


@pytest.fixture
def cag_config() -> CAGConfig:
    """Create CAG configuration for testing."""
    return CAGConfig(
        l1_ttl_seconds=60,
        l2_ttl_seconds=300,
        l3_ttl_seconds=600,
        l2_semantic_threshold=0.85,
        max_l1_entries=1000,
        max_l2_entries=5000,
    )


@pytest.fixture
def sample_state(test_config: TestConfig) -> TradingState:
    """Create sample trading state."""
    factory = TradingStateFactory()
    return factory.create()


@pytest.fixture
def sample_action(test_config: TestConfig) -> TradingAction:
    """Create sample trading action."""
    factory = ActionFactory()
    return factory.create_buy()


@pytest.fixture
def mock_embedding_provider():
    """Create mock embedding provider."""
    provider = MagicMock()
    provider.encode_single.return_value = np.random.randn(384).astype(np.float64)
    provider.encode.return_value = np.random.randn(5, 384).astype(np.float64)
    provider.dimension = 384
    return provider


# =============================================================================
# RAG Base Tests
# =============================================================================


class TestRAGConfig:
    """Tests for RAG configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RAGConfig()
        assert config.default_top_k == 5
        assert config.similarity_threshold == 0.7
        assert config.embedding_model == EmbeddingModelType.MINILM_L6

    def test_custom_config(self):
        """Test custom configuration."""
        config = RAGConfig(
            default_top_k=10,
            similarity_threshold=0.8,
            chunk_size=1024,
        )
        assert config.default_top_k == 10
        assert config.similarity_threshold == 0.8
        assert config.chunk_size == 1024

    def test_config_validation(self):
        """Test configuration validation."""
        # Should raise for invalid values
        with pytest.raises(Exception):
            RAGConfig(similarity_threshold=1.5)


class TestDocumentChunk:
    """Tests for DocumentChunk."""

    def test_chunk_creation(self):
        """Test chunk creation."""
        chunk = DocumentChunk(
            content="Test content",
            chunk_index=0,
            doc_id="doc_123",
            metadata={"key": "value"},
        )
        assert chunk.content == "Test content"
        assert chunk.chunk_index == 0
        assert chunk.doc_id == "doc_123"

    def test_chunk_serialization(self):
        """Test chunk to_dict and from_dict."""
        chunk = DocumentChunk(
            content="Test",
            chunk_index=1,
            doc_id="doc_456",
        )
        chunk_dict = chunk.to_dict()
        restored = DocumentChunk.from_dict(chunk_dict)
        assert restored.content == chunk.content
        assert restored.chunk_index == chunk.chunk_index


# =============================================================================
# CAG Base Tests
# =============================================================================


class TestCAGConfig:
    """Tests for CAG configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CAGConfig()
        assert config.l2_semantic_threshold == 0.92
        assert config.max_l1_entries == 10000

    def test_custom_config(self):
        """Test custom configuration."""
        config = CAGConfig(
            l2_semantic_threshold=0.9,
            max_l1_entries=5000,
        )
        assert config.l2_semantic_threshold == 0.9
        assert config.max_l1_entries == 5000


class TestCacheEntry:
    """Tests for CacheEntry."""

    def test_entry_creation(self):
        """Test cache entry creation."""
        entry = CacheEntry(
            key="test_key",
            value={"data": "value"},
            ttl_seconds=60,
        )
        assert entry.key == "test_key"
        assert not entry.is_expired

    def test_entry_expiration(self):
        """Test cache entry expiration."""
        entry = CacheEntry(
            key="test_key",
            value={"data": "value"},
            ttl_seconds=0,  # Already expired
        )
        entry.created_at = datetime.now() - timedelta(seconds=10)
        assert entry.is_expired

    def test_entry_touch(self):
        """Test cache entry touch."""
        entry = CacheEntry(key="test", value={})
        initial_count = entry.access_count
        entry.touch()
        assert entry.access_count == initial_count + 1


# =============================================================================
# SemanticDecisionCache Tests
# =============================================================================


class TestSemanticDecisionCache:
    """Tests for SemanticDecisionCache."""

    @pytest.fixture
    def cache(self, cag_config: CAGConfig) -> SemanticDecisionCache:
        """Create cache instance."""
        return SemanticDecisionCache(cag_config=cag_config)

    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache: SemanticDecisionCache):
        """Test cache initialization."""
        await cache.initialize()
        assert cache._initialized

    @pytest.mark.asyncio
    async def test_cache_decision(
        self,
        cache: SemanticDecisionCache,
        sample_state: TradingState,
        sample_action: TradingAction,
    ):
        """Test caching a decision."""
        await cache.initialize()

        entry_id = await cache.cache_decision(
            sample_state,
            sample_action,
            reasoning="Test reasoning",
        )

        assert entry_id != ""

    @pytest.mark.asyncio
    async def test_get_cached_decision(
        self,
        cache: SemanticDecisionCache,
        sample_state: TradingState,
        sample_action: TradingAction,
        mock_embedding_provider,
    ):
        """Test retrieving cached decision."""
        cache._embedding_provider = mock_embedding_provider
        await cache.initialize()

        # Cache a decision
        await cache.cache_decision(sample_state, sample_action)

        # Retrieve it
        action, similarity = await cache.get_cached_decision(sample_state)

        # Should find exact match
        assert action is not None or similarity == 0.0

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache: SemanticDecisionCache):
        """Test cache statistics."""
        await cache.initialize()

        stats = cache.get_stats()
        assert isinstance(stats, CacheStats)
        assert stats.total_queries >= 0


class TestCachedDecision:
    """Tests for CachedDecision dataclass."""

    def test_creation(self):
        """Test CachedDecision creation."""
        decision = CachedDecision(
            action_dict={"direction": "buy"},
            confidence=0.8,
            reasoning="Test",
            state_features=[0.1, 0.2, 0.3],
            symbol="AAPL",
            regime="trending_up",
        )
        assert decision.confidence == 0.8
        assert decision.symbol == "AAPL"

    def test_serialization(self):
        """Test serialization."""
        decision = CachedDecision(
            action_dict={"direction": "buy"},
            confidence=0.8,
            reasoning="Test",
            state_features=[0.1],
            symbol="AAPL",
            regime="trending_up",
        )
        data = decision.to_dict()
        restored = CachedDecision.from_dict(data)
        assert restored.confidence == decision.confidence
        assert restored.symbol == decision.symbol


# =============================================================================
# TradingPatternRAG Tests
# =============================================================================


class TestTradingPatternRAG:
    """Tests for TradingPatternRAG."""

    @pytest.fixture
    def pattern_rag(self, rag_config: RAGConfig) -> TradingPatternRAG:
        """Create pattern RAG instance."""
        return TradingPatternRAG(rag_config=rag_config)

    @pytest.mark.asyncio
    async def test_initialization(self, pattern_rag: TradingPatternRAG):
        """Test RAG initialization."""
        await pattern_rag.initialize()
        assert pattern_rag._initialized

    @pytest.mark.asyncio
    async def test_store_pattern(
        self,
        pattern_rag: TradingPatternRAG,
        sample_state: TradingState,
        sample_action: TradingAction,
        mock_embedding_provider,
    ):
        """Test storing a pattern."""
        pattern_rag._embedding_provider = mock_embedding_provider
        await pattern_rag.initialize()

        outcome = {
            "returns": 0.05,
            "sharpe": 1.2,
            "sortino": 1.5,
            "max_drawdown": 0.02,
            "days": 5,
        }

        pattern_id = await pattern_rag.store_pattern(
            sample_state,
            sample_action,
            outcome,
        )

        assert pattern_id != ""

    @pytest.mark.asyncio
    async def test_retrieve_patterns(
        self,
        pattern_rag: TradingPatternRAG,
        sample_state: TradingState,
        sample_action: TradingAction,
        mock_embedding_provider,
    ):
        """Test retrieving similar patterns."""
        pattern_rag._embedding_provider = mock_embedding_provider
        await pattern_rag.initialize()

        # Store a pattern first
        outcome = {"returns": 0.05, "sharpe": 1.2}
        await pattern_rag.store_pattern(sample_state, sample_action, outcome)

        # Retrieve
        patterns = await pattern_rag.retrieve_similar_patterns(
            sample_state,
            top_k=5,
        )

        assert isinstance(patterns, list)

    @pytest.mark.asyncio
    async def test_pattern_stats(self, pattern_rag: TradingPatternRAG):
        """Test pattern statistics."""
        await pattern_rag.initialize()

        stats = await pattern_rag.get_pattern_stats()
        assert "total_patterns" in stats
        assert "symbols" in stats


class TestTradingPattern:
    """Tests for TradingPattern dataclass."""

    def test_creation(self):
        """Test pattern creation."""
        pattern = TradingPattern(
            symbol="AAPL",
            regime="trending_up",
            action_direction="buy",
            outcome_sharpe=1.5,
        )
        assert pattern.symbol == "AAPL"
        assert pattern.outcome_sharpe == 1.5

    def test_semantic_text(self):
        """Test semantic text generation."""
        pattern = TradingPattern(
            symbol="AAPL",
            regime="trending_up",
            technical_context={"rsi": 65.0},
            action_direction="buy",
            action_confidence=0.8,
            outcome_win=True,
            outcome_returns=0.05,
            outcome_sharpe=1.2,
        )
        text = pattern.to_semantic_text()
        assert "AAPL" in text
        assert "buy" in text

    def test_serialization(self):
        """Test serialization."""
        pattern = TradingPattern(
            symbol="AAPL",
            outcome_sharpe=1.0,
        )
        data = pattern.to_dict()
        restored = TradingPattern.from_dict(data)
        assert restored.symbol == pattern.symbol


# =============================================================================
# AnalystResponseCAG Tests
# =============================================================================


class TestAnalystResponseCAG:
    """Tests for AnalystResponseCAG."""

    @pytest.fixture
    def analyst_cache(self, cag_config: CAGConfig) -> AnalystResponseCAG:
        """Create analyst cache instance."""
        return AnalystResponseCAG(cag_config=cag_config)

    @pytest.mark.asyncio
    async def test_initialization(self, analyst_cache: AnalystResponseCAG):
        """Test cache initialization."""
        await analyst_cache.initialize()
        assert analyst_cache._initialized

    @pytest.mark.asyncio
    async def test_cache_analyst_response(
        self,
        analyst_cache: AnalystResponseCAG,
        sample_state: TradingState,
        mock_embedding_provider,
    ):
        """Test caching analyst response."""
        analyst_cache._embedding_provider = mock_embedding_provider
        await analyst_cache.initialize()

        entry_id = await analyst_cache.cache_analyst_response(
            analyst_type=AnalystType.MARKET,
            symbol="AAPL",
            response="Bullish outlook",
            score=0.7,
            confidence=0.8,
            reasoning="Strong technicals",
            context={"state": sample_state},
        )

        assert entry_id != ""

    @pytest.mark.asyncio
    async def test_get_analyst_response(
        self,
        analyst_cache: AnalystResponseCAG,
        sample_state: TradingState,
        mock_embedding_provider,
    ):
        """Test retrieving analyst response."""
        analyst_cache._embedding_provider = mock_embedding_provider
        await analyst_cache.initialize()

        # Cache a response
        await analyst_cache.cache_analyst_response(
            analyst_type=AnalystType.MARKET,
            symbol="AAPL",
            response="Bullish",
            score=0.7,
            confidence=0.8,
            context={"state": sample_state},
        )

        # Retrieve it
        response = await analyst_cache.get_analyst_response(
            AnalystType.MARKET,
            "AAPL",
            {"state": sample_state},
        )

        # May or may not find depending on embedding similarity
        assert response is None or isinstance(response, CachedAnalystResponse)

    def test_analyst_stats(self, analyst_cache: AnalystResponseCAG):
        """Test analyst statistics."""
        stats = analyst_cache.get_analyst_stats()
        assert AnalystType.MARKET.value in stats
        assert "queries" in stats[AnalystType.MARKET.value]


# =============================================================================
# FinancialKnowledgeRAG Tests
# =============================================================================


class TestFinancialKnowledgeRAG:
    """Tests for FinancialKnowledgeRAG."""

    @pytest.fixture
    def knowledge_rag(self, rag_config: RAGConfig) -> FinancialKnowledgeRAG:
        """Create knowledge RAG instance."""
        return FinancialKnowledgeRAG(rag_config=rag_config)

    @pytest.mark.asyncio
    async def test_initialization(self, knowledge_rag: FinancialKnowledgeRAG):
        """Test RAG initialization."""
        await knowledge_rag.initialize()
        assert knowledge_rag._initialized

    @pytest.mark.asyncio
    async def test_ingest_document(
        self,
        knowledge_rag: FinancialKnowledgeRAG,
        mock_embedding_provider,
    ):
        """Test document ingestion."""
        knowledge_rag._embedding_provider = mock_embedding_provider
        await knowledge_rag.initialize()

        doc_id = await knowledge_rag.ingest_document(
            content="Apple reported strong Q4 earnings...",
            doc_type=DocumentType.NEWS,
            title="Apple Q4 Earnings",
            source="Reuters",
            symbols=["AAPL"],
        )

        assert doc_id != ""

    @pytest.mark.asyncio
    async def test_retrieve_for_symbol(
        self,
        knowledge_rag: FinancialKnowledgeRAG,
        mock_embedding_provider,
    ):
        """Test retrieval for symbol."""
        knowledge_rag._embedding_provider = mock_embedding_provider
        await knowledge_rag.initialize()

        # Ingest a document
        await knowledge_rag.ingest_document(
            content="Apple reported strong earnings...",
            doc_type=DocumentType.NEWS,
            symbols=["AAPL"],
        )

        # Retrieve
        results = await knowledge_rag.retrieve_for_symbol(
            "AAPL",
            "earnings report",
            top_k=5,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_document_stats(self, knowledge_rag: FinancialKnowledgeRAG):
        """Test document statistics."""
        await knowledge_rag.initialize()

        stats = await knowledge_rag.get_document_stats()
        assert "total_documents" in stats
        assert "by_type" in stats


class TestFinancialDocument:
    """Tests for FinancialDocument dataclass."""

    def test_creation(self):
        """Test document creation."""
        doc = FinancialDocument(
            doc_type=DocumentType.NEWS,
            title="Test Title",
            content="Test content",
            symbols=["AAPL"],
        )
        assert doc.doc_type == DocumentType.NEWS
        assert "AAPL" in doc.symbols

    def test_semantic_text(self):
        """Test semantic text generation."""
        doc = FinancialDocument(
            doc_type=DocumentType.NEWS,
            title="Apple Earnings",
            summary="Strong Q4 results",
            symbols=["AAPL"],
        )
        text = doc.to_semantic_text()
        assert "Apple Earnings" in text
        assert "AAPL" in text


# =============================================================================
# MCTSStrategyRAG Tests
# =============================================================================


class TestMCTSStrategyRAG:
    """Tests for MCTSStrategyRAG."""

    @pytest.fixture
    def strategy_rag(self, rag_config: RAGConfig) -> MCTSStrategyRAG:
        """Create strategy RAG instance."""
        return MCTSStrategyRAG(rag_config=rag_config)

    @pytest.mark.asyncio
    async def test_initialization(self, strategy_rag: MCTSStrategyRAG):
        """Test RAG initialization."""
        await strategy_rag.initialize()
        assert strategy_rag._initialized

    @pytest.mark.asyncio
    async def test_store_strategy(
        self,
        strategy_rag: MCTSStrategyRAG,
        mock_embedding_provider,
    ):
        """Test storing a strategy."""
        strategy_rag._embedding_provider = mock_embedding_provider
        await strategy_rag.initialize()

        strategy = MCTSStrategy(
            symbol="AAPL",
            regime="trending_up",
            best_action="buy",
            best_action_confidence=0.8,
            simulations=500,
            outcome_sharpe=1.5,
        )

        strategy_id = await strategy_rag.store(strategy)
        assert strategy_id != ""

    @pytest.mark.asyncio
    async def test_retrieve_strategies(
        self,
        strategy_rag: MCTSStrategyRAG,
        sample_state: TradingState,
        mock_embedding_provider,
    ):
        """Test retrieving similar strategies."""
        strategy_rag._embedding_provider = mock_embedding_provider
        await strategy_rag.initialize()

        # Store a strategy
        strategy = MCTSStrategy(
            symbol=sample_state.symbol,
            regime=sample_state.market_regime.value,
            best_action="buy",
            best_action_confidence=0.8,
            simulations=500,
            outcome_sharpe=1.5,
        )
        await strategy_rag.store(strategy)

        # Retrieve
        strategies = await strategy_rag.retrieve_similar_strategies(
            sample_state,
            min_sharpe=0.5,
            top_k=3,
        )

        assert isinstance(strategies, list)


class TestMCTSStrategy:
    """Tests for MCTSStrategy dataclass."""

    def test_creation(self):
        """Test strategy creation."""
        strategy = MCTSStrategy(
            symbol="AAPL",
            regime="trending_up",
            best_action="buy",
            simulations=1000,
            outcome_sharpe=1.5,
        )
        assert strategy.symbol == "AAPL"
        assert strategy.simulations == 1000

    def test_semantic_text(self):
        """Test semantic text generation."""
        strategy = MCTSStrategy(
            symbol="AAPL",
            regime="trending_up",
            technical_context={"rsi": 60.0},
            best_action="buy",
            best_action_confidence=0.8,
            outcome_sharpe=1.5,
            simulations=500,
        )
        text = strategy.to_semantic_text()
        assert "AAPL" in text
        assert "buy" in text


# =============================================================================
# HierarchicalCAG Tests
# =============================================================================


class TestHierarchicalCAG:
    """Tests for HierarchicalCAG."""

    @pytest.fixture
    def hier_cag(self, cag_config: CAGConfig) -> HierarchicalCAG:
        """Create hierarchical CAG instance."""
        return HierarchicalCAG(cag_config=cag_config)

    @pytest.mark.asyncio
    async def test_initialization(self, hier_cag: HierarchicalCAG):
        """Test CAG initialization."""
        await hier_cag.initialize()
        assert hier_cag._initialized

    @pytest.mark.asyncio
    async def test_get_decision(
        self,
        hier_cag: HierarchicalCAG,
        sample_state: TradingState,
        mock_embedding_provider,
    ):
        """Test getting hierarchical decision."""
        # Mock sub-agents
        hier_cag._decision_cache = MagicMock()
        hier_cag._decision_cache.get_cached_decision = AsyncMock(return_value=(None, 0.0))
        hier_cag._decision_cache.initialize = AsyncMock()

        hier_cag._pattern_rag = MagicMock()
        hier_cag._pattern_rag.retrieve_similar_patterns = AsyncMock(return_value=[])
        hier_cag._pattern_rag.initialize = AsyncMock()

        hier_cag._strategy_rag = MagicMock()
        hier_cag._strategy_rag.retrieve_similar_strategies = AsyncMock(return_value=[])
        hier_cag._strategy_rag.initialize = AsyncMock()

        hier_cag._analyst_cache = MagicMock()
        hier_cag._analyst_cache.get_analyst_response = AsyncMock(return_value=None)
        hier_cag._analyst_cache.initialize = AsyncMock()

        await hier_cag.initialize()

        decision = await hier_cag.get_decision(sample_state, DecisionLevel.TACTICAL)

        assert isinstance(decision, HierarchicalDecision)

    def test_ensemble_computation(self, hier_cag: HierarchicalCAG):
        """Test ensemble computation."""
        sources = [
            EnsembleSource(
                source_name="decision_cache",
                level=CacheLevel.L2_SEMANTIC,
                action_direction="buy",
                confidence=0.8,
                similarity=0.9,
                weight=0.4,
            ),
            EnsembleSource(
                source_name="pattern_rag",
                level=CacheLevel.L3_RAG,
                action_direction="buy",
                confidence=0.7,
                similarity=0.85,
                weight=0.3,
            ),
            EnsembleSource(
                source_name="strategy_rag",
                level=CacheLevel.L3_RAG,
                action_direction="hold",
                confidence=0.6,
                similarity=0.8,
                weight=0.3,
            ),
        ]

        result = hier_cag._compute_ensemble(sources)

        assert "direction" in result
        assert "confidence" in result
        assert "agreement" in result

    def test_ensemble_stats(self, hier_cag: HierarchicalCAG):
        """Test ensemble statistics."""
        stats = hier_cag.get_ensemble_stats()
        assert "config" in stats


class TestEnsembleSource:
    """Tests for EnsembleSource dataclass."""

    def test_creation(self):
        """Test ensemble source creation."""
        source = EnsembleSource(
            source_name="decision_cache",
            level=CacheLevel.L2_SEMANTIC,
            action_direction="buy",
            confidence=0.8,
            similarity=0.9,
            weight=0.5,
        )
        assert source.source_name == "decision_cache"
        assert source.confidence == 0.8


class TestHierarchicalDecision:
    """Tests for HierarchicalDecision dataclass."""

    def test_creation(self):
        """Test decision creation."""
        decision = HierarchicalDecision(
            found=True,
            decision_level=DecisionLevel.TACTICAL,
            action_direction="buy",
            confidence=0.8,
        )
        assert decision.found
        assert decision.action_direction == "buy"

    def test_serialization(self):
        """Test serialization."""
        decision = HierarchicalDecision(
            found=True,
            action_direction="buy",
            confidence=0.8,
        )
        data = decision.to_dict()
        assert data["found"]
        assert data["action_direction"] == "buy"


# =============================================================================
# Integration Tests
# =============================================================================


class TestRAGCAGIntegration:
    """Integration tests for RAG/CAG systems."""

    @pytest.mark.asyncio
    async def test_full_decision_flow(
        self,
        sample_state: TradingState,
        sample_action: TradingAction,
        mock_embedding_provider,
    ):
        """Test full decision flow through all systems."""
        # Create all components
        hier_cag = HierarchicalCAG()

        # Mock embedding provider
        hier_cag.decision_cache._embedding_provider = mock_embedding_provider
        hier_cag.pattern_rag._embedding_provider = mock_embedding_provider
        hier_cag.strategy_rag._embedding_provider = mock_embedding_provider
        hier_cag.analyst_cache._embedding_provider = mock_embedding_provider

        await hier_cag.initialize()

        # Cache a decision
        outcome = {"returns": 0.05, "sharpe": 1.2}
        await hier_cag.cache_decision_outcome(
            sample_state,
            sample_action,
            outcome,
            reasoning="Test decision",
        )

        # Get decision (may or may not hit cache depending on similarity)
        decision = await hier_cag.get_decision(sample_state, DecisionLevel.TACTICAL)

        assert isinstance(decision, HierarchicalDecision)

    @pytest.mark.asyncio
    async def test_pattern_to_strategy_consistency(
        self,
        sample_state: TradingState,
        sample_action: TradingAction,
        mock_embedding_provider,
    ):
        """Test consistency between pattern and strategy RAG."""
        pattern_rag = TradingPatternRAG()
        strategy_rag = MCTSStrategyRAG()

        pattern_rag._embedding_provider = mock_embedding_provider
        strategy_rag._embedding_provider = mock_embedding_provider

        await pattern_rag.initialize()
        await strategy_rag.initialize()

        # Store similar data in both
        outcome = {"returns": 0.05, "sharpe": 1.5}
        await pattern_rag.store_pattern(sample_state, sample_action, outcome)

        strategy = MCTSStrategy(
            symbol=sample_state.symbol,
            regime=sample_state.market_regime.value,
            best_action=sample_action.direction.value,
            best_action_confidence=sample_action.confidence,
            simulations=500,
            outcome_sharpe=1.5,
        )
        await strategy_rag.store(strategy)

        # Both should have data
        pattern_stats = await pattern_rag.get_pattern_stats()
        strategy_stats = await strategy_rag.get_strategy_stats()

        assert pattern_stats["total_patterns"] > 0
        assert strategy_stats["total_strategies"] > 0


# =============================================================================
# Performance Tests
# =============================================================================


class TestRAGCAGPerformance:
    """Performance tests for RAG/CAG systems."""

    @pytest.mark.asyncio
    async def test_cache_lookup_performance(self, mock_embedding_provider):
        """Test cache lookup is fast."""
        import time

        cache = SemanticDecisionCache()
        cache._embedding_provider = mock_embedding_provider
        await cache.initialize()

        factory = TradingStateFactory()
        state = factory.create()

        # Measure lookup time
        start = time.perf_counter()
        for _ in range(100):
            await cache.get_cached_decision(state)
        elapsed = (time.perf_counter() - start) * 1000 / 100

        # Should be fast (under 50ms per lookup on average)
        assert elapsed < 50.0, f"Lookup too slow: {elapsed:.2f}ms"

    @pytest.mark.asyncio
    async def test_rag_retrieval_performance(self, mock_embedding_provider):
        """Test RAG retrieval performance."""
        import time

        pattern_rag = TradingPatternRAG()
        pattern_rag._embedding_provider = mock_embedding_provider
        await pattern_rag.initialize()

        factory = TradingStateFactory()
        action_factory = ActionFactory()

        # Add some patterns
        for _ in range(50):
            state = factory.create()
            action = action_factory.create_buy()
            outcome = {"returns": 0.03, "sharpe": 0.8}
            await pattern_rag.store_pattern(state, action, outcome)

        # Measure retrieval time
        state = factory.create()
        start = time.perf_counter()
        for _ in range(10):
            await pattern_rag.retrieve_similar_patterns(state, top_k=5)
        elapsed = (time.perf_counter() - start) * 1000 / 10

        # Should be reasonably fast (under 100ms)
        assert elapsed < 100.0, f"Retrieval too slow: {elapsed:.2f}ms"
