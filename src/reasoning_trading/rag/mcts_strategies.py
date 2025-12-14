"""
MCTS Strategy RAG for storing successful search strategies.

Stores and retrieves successful MCTS search trees and decision paths
to inform future decision making and reduce search time.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

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
    from reasoning_trading.core.state import TradingState
    from reasoning_trading.mcts.node import Node


class MCTSStrategyConfig(BaseSettings):
    """Configuration specific to MCTS strategy RAG."""

    model_config = SettingsConfigDict(
        env_prefix="MCTS_RAG_",
        case_sensitive=False,
        extra="ignore",
    )

    # Storage thresholds
    min_simulations: int = Field(
        default=100,
        ge=10,
        le=10000,
        description="Minimum simulations for strategy to be stored",
    )
    min_sharpe_to_store: float = Field(
        default=0.3,
        ge=-5.0,
        le=10.0,
        description="Minimum Sharpe ratio to store strategy",
    )
    min_confidence: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to store strategy",
    )

    # Retrieval settings
    max_strategies_per_symbol: int = Field(
        default=500,
        ge=50,
        le=10000,
        description="Maximum strategies per symbol",
    )
    strategy_dedup_threshold: float = Field(
        default=0.95,
        ge=0.8,
        le=1.0,
        description="Similarity threshold for deduplication",
    )

    # Path encoding
    max_path_depth: int = Field(
        default=10,
        ge=3,
        le=50,
        description="Maximum decision path depth to encode",
    )
    include_action_params: bool = Field(
        default=True,
        description="Include action parameters in path encoding",
    )

    # Eviction settings
    eviction_retention_rate: float = Field(
        default=0.8,
        ge=0.5,
        le=0.95,
        description="Fraction of strategies to retain during eviction (best by Sharpe)",
    )


@dataclass
class MCTSStrategy:
    """A stored MCTS strategy with context and performance."""

    # Identity
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Context
    symbol: str = ""
    regime: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Root state features
    root_state_features: dict[str, float] = field(default_factory=dict)
    technical_context: dict[str, float] = field(default_factory=dict)
    analyst_consensus: float = 0.0

    # Decision path
    path_actions: list[str] = field(default_factory=list)
    path_values: list[float] = field(default_factory=list)
    path_visits: list[int] = field(default_factory=list)
    path_depth: int = 0

    # Best action
    best_action: str = ""
    best_action_params: dict[str, float] = field(default_factory=dict)
    best_action_confidence: float = 0.0

    # Performance
    simulations: int = 0
    tree_depth: int = 0
    outcome_returns: float = 0.0
    outcome_sharpe: float = 0.0
    computation_time_ms: float = 0.0

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "regime": self.regime,
            "timestamp": self.timestamp.isoformat(),
            "root_state_features": self.root_state_features,
            "technical_context": self.technical_context,
            "analyst_consensus": self.analyst_consensus,
            "path_actions": self.path_actions,
            "path_values": self.path_values,
            "path_visits": self.path_visits,
            "path_depth": self.path_depth,
            "best_action": self.best_action,
            "best_action_params": self.best_action_params,
            "best_action_confidence": self.best_action_confidence,
            "simulations": self.simulations,
            "tree_depth": self.tree_depth,
            "outcome_returns": self.outcome_returns,
            "outcome_sharpe": self.outcome_sharpe,
            "computation_time_ms": self.computation_time_ms,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCTSStrategy:
        """Create from dictionary."""
        return cls(
            strategy_id=data.get("strategy_id", str(uuid.uuid4())),
            symbol=data.get("symbol", ""),
            regime=data.get("regime", ""),
            timestamp=datetime.fromisoformat(
                data.get("timestamp", datetime.now().isoformat())
            ),
            root_state_features=data.get("root_state_features", {}),
            technical_context=data.get("technical_context", {}),
            analyst_consensus=data.get("analyst_consensus", 0.0),
            path_actions=data.get("path_actions", []),
            path_values=data.get("path_values", []),
            path_visits=data.get("path_visits", []),
            path_depth=data.get("path_depth", 0),
            best_action=data.get("best_action", ""),
            best_action_params=data.get("best_action_params", {}),
            best_action_confidence=data.get("best_action_confidence", 0.0),
            simulations=data.get("simulations", 0),
            tree_depth=data.get("tree_depth", 0),
            outcome_returns=data.get("outcome_returns", 0.0),
            outcome_sharpe=data.get("outcome_sharpe", 0.0),
            computation_time_ms=data.get("computation_time_ms", 0.0),
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
            for key in ["rsi", "macd", "adx", "volatility"]:
                if key in self.technical_context:
                    value = self.technical_context[key]
                    tech_parts.append(f"{key}={value:.1f}")
            if tech_parts:
                parts.append(f"Technical: {', '.join(tech_parts)}")

        # Consensus
        sign = "+" if self.analyst_consensus > 0 else ""
        parts.append(f"Consensus: {sign}{self.analyst_consensus:.2f}")

        # Path summary
        if self.path_actions:
            path_summary = " -> ".join(self.path_actions[:5])
            parts.append(f"Path: {path_summary}")

        # Best action
        parts.append(f"Best action: {self.best_action}")
        parts.append(f"Confidence: {self.best_action_confidence:.2f}")

        # Performance
        parts.append(f"Sharpe: {self.outcome_sharpe:.2f}")
        parts.append(f"Simulations: {self.simulations}")

        return " | ".join(parts)

    @classmethod
    def from_mcts_tree(
        cls,
        root_state: TradingState,
        root_node: Node,
        best_path: list[Node],
        outcome: dict[str, float],
        computation_time_ms: float = 0.0,
    ) -> MCTSStrategy:
        """
        Create strategy from MCTS tree.

        Args:
            root_state: Root state of the search
            root_node: Root node of MCTS tree
            best_path: Best path through tree
            outcome: Outcome metrics
            computation_time_ms: Search computation time

        Returns:
            MCTSStrategy instance
        """
        # Extract technical context
        ind = root_state.technical_indicators
        technical_context = {
            "rsi": ind.rsi_14 or 50.0,
            "macd": ind.macd or 0.0,
            "macd_histogram": ind.macd_histogram or 0.0,
            "adx": ind.adx_14 or 25.0,
            "volatility": ind.volatility_20 or 0.02,
        }

        # Extract path info
        path_actions = []
        path_values = []
        path_visits = []

        for node in best_path:
            if node.action is not None:
                path_actions.append(node.action.direction.value)
                path_values.append(node.value)
                path_visits.append(node.visits)

        # Best action from first action in path
        best_action = ""
        best_action_params = {}
        best_action_confidence = 0.0

        if best_path and len(best_path) > 1:
            first_action_node = best_path[1]
            if first_action_node.action is not None:
                best_action = first_action_node.action.direction.value
                best_action_params = {
                    "size": first_action_node.action.position_size.size_fraction,
                    "stop_loss": first_action_node.action.stop_loss.stop_loss_pct,
                }
                best_action_confidence = first_action_node.action.confidence

        return cls(
            symbol=root_state.symbol,
            regime=root_state.market_regime.value,
            timestamp=root_state.timestamp,
            technical_context=technical_context,
            analyst_consensus=root_state.analyst_signals.weighted_consensus(),
            path_actions=path_actions,
            path_values=path_values,
            path_visits=path_visits,
            path_depth=len(best_path),
            best_action=best_action,
            best_action_params=best_action_params,
            best_action_confidence=best_action_confidence,
            simulations=root_node.visits,
            tree_depth=cls._compute_tree_depth(root_node),
            outcome_returns=outcome.get("returns", 0.0),
            outcome_sharpe=outcome.get("sharpe", 0.0),
            computation_time_ms=computation_time_ms,
        )

    @staticmethod
    def _compute_tree_depth(node: Node, depth: int = 0) -> int:
        """Compute maximum depth of tree."""
        if not node.children:
            return depth
        child_depths = [
            MCTSStrategy._compute_tree_depth(child, depth + 1)
            for child in node.children
        ]
        return max(child_depths) if child_depths else depth


class MCTSStrategyRAG(BaseRAG[MCTSStrategy]):
    """
    RAG system for MCTS strategies.

    Stores successful MCTS search results to:
    - Guide future searches
    - Reduce computation time
    - Transfer knowledge between similar states
    """

    def __init__(
        self,
        rag_config: RAGConfig | None = None,
        strategy_config: MCTSStrategyConfig | None = None,
    ):
        super().__init__(config=rag_config)
        self.strategy_config = strategy_config or MCTSStrategyConfig()

        # Storage: symbol -> list of (embedding, strategy)
        self._strategies: dict[str, list[tuple[NDArray[np.float64], MCTSStrategy]]] = {}

    async def _setup_collections(self) -> None:
        """Setup vector database collections."""
        if self.config.vector_db_type.value == "chromadb":
            try:
                import chromadb

                self._client = chromadb.PersistentClient(path=str(self.config.persist_dir))
                self._collection = self._client.get_or_create_collection(
                    name=self.config.strategies_collection,
                    metadata={"hnsw:space": self.config.distance_metric},
                )
            except ImportError:
                pass

    async def store(
        self,
        document: MCTSStrategy,
        **kwargs,
    ) -> str:
        """
        Store an MCTS strategy.

        Args:
            document: Strategy to store

        Returns:
            Strategy ID
        """
        # Check thresholds
        if document.simulations < self.strategy_config.min_simulations:
            return ""
        if document.outcome_sharpe < self.strategy_config.min_sharpe_to_store:
            return ""
        if document.best_action_confidence < self.strategy_config.min_confidence:
            return ""

        # Generate embedding
        semantic_text = document.to_semantic_text()
        embedding = self.embedding_provider.encode_single(semantic_text)

        # Check for duplicates
        if await self._is_duplicate(document.symbol, embedding):
            return ""

        # Store
        symbol = document.symbol
        if symbol not in self._strategies:
            self._strategies[symbol] = []

        # Check capacity
        if len(self._strategies[symbol]) >= self.strategy_config.max_strategies_per_symbol:
            await self._evict_strategies(symbol)

        self._strategies[symbol].append((embedding, document))

        return document.strategy_id

    async def store_successful_tree(
        self,
        root_state: TradingState,
        root_node: Node,
        best_path: list[Node],
        outcome: dict[str, float],
        computation_time_ms: float = 0.0,
    ) -> str:
        """
        Store a successful MCTS tree.

        Convenience method for storing strategies.

        Args:
            root_state: Root state of search
            root_node: Root node of tree
            best_path: Best path through tree
            outcome: Outcome metrics
            computation_time_ms: Search time

        Returns:
            Strategy ID
        """
        strategy = MCTSStrategy.from_mcts_tree(
            root_state, root_node, best_path, outcome, computation_time_ms
        )
        return await self.store(strategy)

    async def _is_duplicate(
        self,
        symbol: str,
        embedding: NDArray[np.float64],
    ) -> bool:
        """Check if similar strategy exists."""
        strategies = self._strategies.get(symbol, [])

        for stored_embedding, _ in strategies:
            similarity = self._compute_similarity(embedding, stored_embedding)
            if similarity >= self.strategy_config.strategy_dedup_threshold:
                return True

        return False

    async def _evict_strategies(self, symbol: str) -> None:
        """Evict strategies to make room."""
        strategies = self._strategies.get(symbol, [])
        if not strategies:
            return

        # Sort by Sharpe, keep best performers
        strategies.sort(key=lambda x: x[1].outcome_sharpe, reverse=True)
        keep_count = int(len(strategies) * self.strategy_config.eviction_retention_rate)
        self._strategies[symbol] = strategies[:keep_count]

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        **filters,
    ) -> list[RetrievalResult]:
        """
        Retrieve similar strategies.

        Args:
            query: Query string
            top_k: Number of results
            **filters: symbol, regime, min_sharpe filters

        Returns:
            List of retrieval results
        """
        k = top_k or self.config.default_top_k

        symbol_filter = filters.get("symbol")
        regime_filter = filters.get("regime")
        min_sharpe = filters.get("min_sharpe", self.strategy_config.min_sharpe_to_store)

        query_embedding = self.embedding_provider.encode_single(query)

        results = []

        symbols_to_search = (
            [symbol_filter] if symbol_filter else list(self._strategies.keys())
        )

        for symbol in symbols_to_search:
            strategies = self._strategies.get(symbol, [])

            for stored_embedding, strategy in strategies:
                # Apply filters
                if regime_filter and strategy.regime != regime_filter:
                    continue
                if strategy.outcome_sharpe < min_sharpe:
                    continue

                similarity = self._compute_similarity(query_embedding, stored_embedding)

                if similarity >= self.config.similarity_threshold:
                    results.append(
                        RetrievalResult(
                            content=strategy.to_semantic_text(),
                            similarity=similarity,
                            doc_id=strategy.strategy_id,
                            doc_type="mcts_strategy",
                            metadata=strategy.to_dict(),
                            score=similarity * (1 + strategy.outcome_sharpe / 10),  # Boost by Sharpe
                        )
                    )

        results.sort(key=lambda x: x.score, reverse=True)

        for i, result in enumerate(results):
            result.rank = i + 1

        return results[:k]

    async def retrieve_similar_strategies(
        self,
        state: TradingState,
        min_sharpe: float = 0.5,
        top_k: int = 3,
    ) -> list[tuple[MCTSStrategy, float]]:
        """
        Retrieve similar strategies for a state.

        Convenience method for strategy retrieval.

        Args:
            state: Current trading state
            min_sharpe: Minimum Sharpe filter
            top_k: Number of results

        Returns:
            List of (MCTSStrategy, similarity) tuples
        """
        # Create query from state
        ind = state.technical_indicators
        consensus = state.analyst_signals.weighted_consensus()

        query = (
            f"Symbol: {state.symbol} | Regime: {state.market_regime.value} | "
            f"RSI: {ind.rsi_14 or 50:.0f} | MACD: {ind.macd or 0:.2f} | "
            f"Consensus: {consensus:+.2f}"
        )

        results = await self.retrieve(
            query,
            top_k=top_k,
            symbol=state.symbol,
            regime=state.market_regime.value,
            min_sharpe=min_sharpe,
        )

        return [
            (MCTSStrategy.from_dict(r.metadata), r.similarity)
            for r in results
        ]

    async def delete(self, doc_id: str) -> bool:
        """Delete a strategy by ID."""
        for symbol in list(self._strategies.keys()):
            self._strategies[symbol] = [
                (e, s) for e, s in self._strategies[symbol] if s.strategy_id != doc_id
            ]
        return True

    async def get_strategy_stats(self) -> dict[str, Any]:
        """Get strategy statistics."""
        total_strategies = sum(len(s) for s in self._strategies.values())

        all_sharpes = [
            s.outcome_sharpe for strategies in self._strategies.values() for _, s in strategies
        ]
        avg_sharpe = np.mean(all_sharpes) if all_sharpes else 0.0

        all_sims = [
            s.simulations for strategies in self._strategies.values() for _, s in strategies
        ]
        avg_sims = np.mean(all_sims) if all_sims else 0.0

        return {
            "total_strategies": total_strategies,
            "symbols": len(self._strategies),
            "avg_sharpe": avg_sharpe,
            "avg_simulations": avg_sims,
            "strategies_per_symbol": {
                symbol: len(strategies) for symbol, strategies in self._strategies.items()
            },
        }

    async def get_best_strategies(
        self,
        symbol: str,
        top_k: int = 5,
    ) -> list[MCTSStrategy]:
        """Get best performing strategies for a symbol."""
        strategies = self._strategies.get(symbol, [])

        sorted_strategies = sorted(
            [s for _, s in strategies],
            key=lambda x: x.outcome_sharpe,
            reverse=True,
        )

        return sorted_strategies[:top_k]
