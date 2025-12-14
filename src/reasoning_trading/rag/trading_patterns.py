"""
Trading Pattern RAG for historical pattern retrieval.

Stores historical trading patterns with outcomes for retrieval-augmented
decision making based on similar past market conditions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.rag.base import (
    BaseRAG,
    RAGConfig,
    RetrievalResult,
)

if TYPE_CHECKING:
    from reasoning_trading.core.actions import TradingAction
    from reasoning_trading.core.state import TradingState


class TradingPatternConfig(BaseSettings):
    """Configuration specific to trading pattern RAG."""

    model_config = SettingsConfigDict(
        env_prefix="PATTERN_RAG_",
        case_sensitive=False,
        extra="ignore",
    )

    # Pattern storage settings
    min_outcome_days: int = Field(
        default=1,
        ge=1,
        le=30,
        description="Minimum days after trade to record outcome",
    )
    max_outcome_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Maximum days to track outcome",
    )

    # Performance thresholds
    min_sharpe_to_store: float = Field(
        default=-2.0,
        ge=-10.0,
        le=10.0,
        description="Minimum Sharpe ratio to store (allows learning from failures)",
    )
    success_sharpe_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=5.0,
        description="Sharpe ratio threshold to consider pattern successful",
    )

    # Retrieval settings
    regime_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for regime matching in similarity",
    )
    technical_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for technical indicator similarity",
    )
    outcome_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for favorable outcome filtering",
    )

    # Collection settings
    max_patterns_per_symbol: int = Field(
        default=1000,
        ge=100,
        le=100000,
        description="Maximum patterns to store per symbol",
    )
    dedup_similarity_threshold: float = Field(
        default=0.98,
        ge=0.9,
        le=1.0,
        description="Similarity threshold for deduplication",
    )

    # Eviction settings
    eviction_retention_rate: float = Field(
        default=0.8,
        ge=0.5,
        le=0.95,
        description="Fraction of patterns to retain during eviction (best by Sharpe)",
    )


@dataclass
class TradingPattern:
    """A stored trading pattern with context and outcome."""

    # Identity
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Context
    symbol: str = ""
    regime: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # State features
    technical_context: dict[str, float] = field(default_factory=dict)
    analyst_signals: dict[str, float] = field(default_factory=dict)
    portfolio_context: dict[str, float] = field(default_factory=dict)

    # Action taken
    action_direction: str = ""
    action_size: float = 0.0
    action_stop_loss: float = 0.0
    action_confidence: float = 0.0

    # Outcome
    outcome_returns: float = 0.0
    outcome_sharpe: float = 0.0
    outcome_sortino: float = 0.0
    outcome_max_drawdown: float = 0.0
    outcome_win: bool = False
    outcome_days: int = 0

    # Reasoning and metadata
    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "symbol": self.symbol,
            "regime": self.regime,
            "timestamp": self.timestamp.isoformat(),
            "technical_context": self.technical_context,
            "analyst_signals": self.analyst_signals,
            "portfolio_context": self.portfolio_context,
            "action_direction": self.action_direction,
            "action_size": self.action_size,
            "action_stop_loss": self.action_stop_loss,
            "action_confidence": self.action_confidence,
            "outcome_returns": self.outcome_returns,
            "outcome_sharpe": self.outcome_sharpe,
            "outcome_sortino": self.outcome_sortino,
            "outcome_max_drawdown": self.outcome_max_drawdown,
            "outcome_win": self.outcome_win,
            "outcome_days": self.outcome_days,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TradingPattern:
        """Create from dictionary."""
        return cls(
            pattern_id=data.get("pattern_id", str(uuid.uuid4())),
            symbol=data.get("symbol", ""),
            regime=data.get("regime", ""),
            timestamp=datetime.fromisoformat(
                data.get("timestamp", datetime.now().isoformat())
            ),
            technical_context=data.get("technical_context", {}),
            analyst_signals=data.get("analyst_signals", {}),
            portfolio_context=data.get("portfolio_context", {}),
            action_direction=data.get("action_direction", ""),
            action_size=data.get("action_size", 0.0),
            action_stop_loss=data.get("action_stop_loss", 0.0),
            action_confidence=data.get("action_confidence", 0.0),
            outcome_returns=data.get("outcome_returns", 0.0),
            outcome_sharpe=data.get("outcome_sharpe", 0.0),
            outcome_sortino=data.get("outcome_sortino", 0.0),
            outcome_max_drawdown=data.get("outcome_max_drawdown", 0.0),
            outcome_win=data.get("outcome_win", False),
            outcome_days=data.get("outcome_days", 0),
            reasoning=data.get("reasoning", ""),
            metadata=data.get("metadata", {}),
        )

    def to_semantic_text(self) -> str:
        """Convert to semantic text for embedding."""
        parts = [
            f"Symbol: {self.symbol}",
            f"Regime: {self.regime}",
        ]

        # Technical context
        if self.technical_context:
            tech_parts = []
            for key, value in self.technical_context.items():
                if isinstance(value, float):
                    tech_parts.append(f"{key}={value:.2f}")
            if tech_parts:
                parts.append(f"Technical: {', '.join(tech_parts)}")

        # Analyst signals
        if self.analyst_signals:
            signal_parts = []
            for key, value in self.analyst_signals.items():
                if isinstance(value, float):
                    sign = "+" if value > 0 else ""
                    signal_parts.append(f"{key}={sign}{value:.2f}")
            if signal_parts:
                parts.append(f"Signals: {', '.join(signal_parts)}")

        # Action
        parts.append(
            f"Action: {self.action_direction} {self.action_size*100:.1f}% "
            f"(confidence={self.action_confidence:.2f})"
        )

        # Outcome
        outcome_str = "WIN" if self.outcome_win else "LOSS"
        parts.append(
            f"Outcome: {outcome_str} {self.outcome_returns*100:.2f}% "
            f"(Sharpe={self.outcome_sharpe:.2f})"
        )

        return " | ".join(parts)

    @classmethod
    def from_state_action_outcome(
        cls,
        state: TradingState,
        action: TradingAction,
        outcome: dict[str, float],
        reasoning: str = "",
        success_sharpe_threshold: float | None = None,
    ) -> TradingPattern:
        """
        Create pattern from state, action, and outcome.

        Args:
            state: Trading state at decision time
            action: Action taken
            outcome: Outcome metrics (returns, sharpe, etc.)
            reasoning: Reasoning for the action
            success_sharpe_threshold: Threshold for considering pattern successful.
                If None, uses default from TradingPatternConfig.
        """
        # Extract technical context
        ind = state.technical_indicators
        technical_context = {
            "rsi": ind.rsi_14 or 50.0,
            "macd": ind.macd or 0.0,
            "macd_histogram": ind.macd_histogram or 0.0,
            "adx": ind.adx_14 or 25.0,
            "volatility": ind.volatility_20 or 0.02,
            "stochastic_k": ind.stochastic_k or 50.0,
        }

        # Extract analyst signals
        signals = state.analyst_signals
        analyst_signals = {
            "market": signals.market_analyst_score,
            "news": signals.news_analyst_score,
            "social": signals.social_sentiment_score,
            "fundamental": signals.fundamental_analyst_score,
            "macro": signals.macro_analyst_score,
            "consensus": signals.weighted_consensus(),
        }

        # Extract portfolio context
        portfolio_context = {
            "position_pct": state.portfolio.get_position_pct(state.symbol),
            "drawdown": state.portfolio.current_drawdown,
            "cash_ratio": (
                state.portfolio.cash_balance / max(state.portfolio.portfolio_value, 1)
            ),
        }

        # Determine if win based on Sharpe - use provided threshold or config default
        threshold = (
            success_sharpe_threshold
            if success_sharpe_threshold is not None
            else TradingPatternConfig().success_sharpe_threshold
        )
        outcome_win = outcome.get("sharpe", 0.0) >= threshold

        return cls(
            symbol=state.symbol,
            regime=state.market_regime.value,
            timestamp=state.timestamp,
            technical_context=technical_context,
            analyst_signals=analyst_signals,
            portfolio_context=portfolio_context,
            action_direction=action.direction.value,
            action_size=action.position_size.size_fraction,
            action_stop_loss=action.stop_loss.stop_loss_pct,
            action_confidence=action.confidence,
            outcome_returns=outcome.get("returns", 0.0),
            outcome_sharpe=outcome.get("sharpe", 0.0),
            outcome_sortino=outcome.get("sortino", 0.0),
            outcome_max_drawdown=outcome.get("max_drawdown", 0.0),
            outcome_win=outcome_win,
            outcome_days=outcome.get("days", 0),
            reasoning=reasoning or action.reasoning,
        )


class TradingPatternRAG(BaseRAG[TradingPattern]):
    """
    RAG system for historical trading patterns.

    Stores and retrieves trading patterns based on:
    - Technical indicator similarity
    - Market regime matching
    - Historical outcome performance
    """

    def __init__(
        self,
        rag_config: RAGConfig | None = None,
        pattern_config: TradingPatternConfig | None = None,
    ):
        super().__init__(config=rag_config)
        self.pattern_config = pattern_config or TradingPatternConfig()

        # In-memory storage: symbol -> list of (embedding, pattern)
        self._patterns: dict[str, list[tuple[NDArray[np.float64], TradingPattern]]] = {}

    async def _setup_collections(self) -> None:
        """Setup vector database collections."""
        # For in-memory, just initialize empty storage
        # For ChromaDB, would create collection here
        if self.config.vector_db_type.value == "chromadb":
            try:
                import chromadb

                self._client = chromadb.PersistentClient(path=str(self.config.persist_dir))
                self._collection = self._client.get_or_create_collection(
                    name=self.config.patterns_collection,
                    metadata={"hnsw:space": self.config.distance_metric},
                )
            except ImportError:
                pass  # Fall back to in-memory

    async def store(
        self,
        document: TradingPattern,
        **kwargs,
    ) -> str:
        """
        Store a trading pattern.

        Args:
            document: TradingPattern to store

        Returns:
            Pattern ID
        """
        # Check minimum Sharpe
        if document.outcome_sharpe < self.pattern_config.min_sharpe_to_store:
            return ""

        # Generate embedding
        semantic_text = document.to_semantic_text()
        embedding = self.embedding_provider.encode_single(semantic_text)

        # Check for duplicates
        if await self._is_duplicate(document.symbol, embedding):
            return ""

        # Store in memory
        symbol = document.symbol
        if symbol not in self._patterns:
            self._patterns[symbol] = []

        # Check capacity
        if len(self._patterns[symbol]) >= self.pattern_config.max_patterns_per_symbol:
            await self._evict_patterns(symbol)

        self._patterns[symbol].append((embedding, document))

        return document.pattern_id

    async def store_pattern(
        self,
        state: TradingState,
        action: TradingAction,
        outcome: dict[str, float],
        reasoning: str = "",
    ) -> str:
        """
        Store a pattern from state, action, and outcome.

        Convenience method for storing patterns.

        Args:
            state: Trading state at decision time
            action: Action taken
            outcome: Outcome metrics (returns, sharpe, etc.)
            reasoning: Reasoning for the action

        Returns:
            Pattern ID
        """
        pattern = TradingPattern.from_state_action_outcome(
            state,
            action,
            outcome,
            reasoning,
            success_sharpe_threshold=self.pattern_config.success_sharpe_threshold,
        )
        return await self.store(pattern)

    async def _is_duplicate(
        self,
        symbol: str,
        embedding: NDArray[np.float64],
    ) -> bool:
        """Check if a similar pattern already exists."""
        patterns = self._patterns.get(symbol, [])

        for stored_embedding, _ in patterns:
            similarity = self._compute_similarity(embedding, stored_embedding)
            if similarity >= self.pattern_config.dedup_similarity_threshold:
                return True

        return False

    async def _evict_patterns(self, symbol: str) -> None:
        """Evict patterns to make room for new ones."""
        patterns = self._patterns.get(symbol, [])
        if not patterns:
            return

        # Sort by outcome quality (keep best performing)
        patterns.sort(key=lambda x: x[1].outcome_sharpe, reverse=True)

        # Keep top 80%
        keep_count = int(len(patterns) * self.pattern_config.eviction_retention_rate)
        self._patterns[symbol] = patterns[:keep_count]

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        **filters,
    ) -> list[RetrievalResult]:
        """
        Retrieve similar patterns.

        Args:
            query: Query string (semantic description)
            top_k: Number of results
            **filters: symbol, regime, min_sharpe filters

        Returns:
            List of retrieval results
        """
        k = top_k or self.config.default_top_k

        # Get filters
        symbol_filter = filters.get("symbol")
        regime_filter = filters.get("regime")
        min_sharpe = filters.get("min_sharpe", self.pattern_config.min_sharpe_to_store)
        successful_only = filters.get("successful_only", False)

        # Generate query embedding
        query_embedding = self.embedding_provider.encode_single(query)

        results = []

        # Search relevant symbol collections
        symbols_to_search = (
            [symbol_filter] if symbol_filter else list(self._patterns.keys())
        )

        for symbol in symbols_to_search:
            patterns = self._patterns.get(symbol, [])

            for stored_embedding, pattern in patterns:
                # Apply filters
                if regime_filter and pattern.regime != regime_filter:
                    continue
                if pattern.outcome_sharpe < min_sharpe:
                    continue
                if successful_only and not pattern.outcome_win:
                    continue

                # Compute similarity
                similarity = self._compute_similarity(query_embedding, stored_embedding)

                if similarity >= self.config.similarity_threshold:
                    results.append(
                        RetrievalResult(
                            content=pattern.to_semantic_text(),
                            similarity=similarity,
                            doc_id=pattern.pattern_id,
                            doc_type="trading_pattern",
                            metadata=pattern.to_dict(),
                        )
                    )

        # Sort by similarity and return top-k
        results.sort(key=lambda x: x.similarity, reverse=True)

        # Apply ranking
        for i, result in enumerate(results):
            result.rank = i + 1
            result.score = result.similarity

        return results[:k]

    async def retrieve_similar_patterns(
        self,
        state: TradingState,
        top_k: int = 5,
        regime_filter: str | None = None,
        successful_only: bool = False,
    ) -> list[tuple[TradingPattern, float]]:
        """
        Retrieve similar patterns for a trading state.

        Convenience method for pattern retrieval.

        Args:
            state: Current trading state
            top_k: Number of results
            regime_filter: Filter by regime
            successful_only: Only return successful patterns

        Returns:
            List of (TradingPattern, similarity) tuples
        """
        # Create query from state
        query_pattern = TradingPattern.from_state_action_outcome(
            state,
            # Dummy action for query generation
            self._create_dummy_action(),
            {},
            success_sharpe_threshold=self.pattern_config.success_sharpe_threshold,
        )
        query_text = query_pattern.to_semantic_text()

        # Use regime from state if not overridden
        regime = regime_filter or state.market_regime.value

        results = await self.retrieve(
            query_text,
            top_k=top_k,
            symbol=state.symbol,
            regime=regime,
            successful_only=successful_only,
        )

        return [
            (TradingPattern.from_dict(r.metadata), r.similarity)
            for r in results
        ]

    def _create_dummy_action(self) -> TradingAction:
        """Create a dummy action for query generation."""
        from reasoning_trading.core.actions import (
            PositionSizeAction,
            StopLossAction,
            TimeHorizon,
            TradingAction,
            TradingDirection,
        )

        return TradingAction(
            direction=TradingDirection.HOLD,
            position_size=PositionSizeAction(size_fraction=0.0),
            stop_loss=StopLossAction(stop_loss_pct=0.05),
            time_horizon=TimeHorizon.INTRADAY,
            confidence=0.5,
        )

    async def delete(self, doc_id: str) -> bool:
        """Delete a pattern by ID."""
        for symbol in list(self._patterns.keys()):
            self._patterns[symbol] = [
                (e, p) for e, p in self._patterns[symbol] if p.pattern_id != doc_id
            ]
        return True

    async def get_pattern_stats(self) -> dict[str, Any]:
        """Get statistics about stored patterns."""
        total_patterns = sum(len(p) for p in self._patterns.values())
        successful_patterns = sum(
            sum(1 for _, p in patterns if p.outcome_win)
            for patterns in self._patterns.values()
        )

        avg_sharpe = 0.0
        all_sharpes = [
            p.outcome_sharpe
            for patterns in self._patterns.values()
            for _, p in patterns
        ]
        if all_sharpes:
            avg_sharpe = np.mean(all_sharpes)

        return {
            "total_patterns": total_patterns,
            "symbols": len(self._patterns),
            "successful_patterns": successful_patterns,
            "success_rate": successful_patterns / max(total_patterns, 1),
            "avg_sharpe": avg_sharpe,
            "patterns_per_symbol": {
                symbol: len(patterns) for symbol, patterns in self._patterns.items()
            },
        }

    async def get_best_patterns(
        self,
        symbol: str,
        top_k: int = 10,
    ) -> list[TradingPattern]:
        """Get top performing patterns for a symbol."""
        patterns = self._patterns.get(symbol, [])

        # Sort by Sharpe ratio
        sorted_patterns = sorted(
            [p for _, p in patterns],
            key=lambda x: x.outcome_sharpe,
            reverse=True,
        )

        return sorted_patterns[:top_k]
