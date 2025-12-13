"""
MCTS Orchestrator using LangGraph supervisor pattern.

Provides high-level orchestration for MCTS phases:
- Hierarchical search coordination
- Regime-aware search configuration
- Integration with Lambda architecture
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from reasoning_trading.langgraph.graph import (
    MCTSGraph,
    MCTSGraphBuilder,
    MCTSGraphConfig,
    MCTSGraphResult,
)
from reasoning_trading.langgraph.nodes import NodeConfig

if TYPE_CHECKING:
    from reasoning_trading.core.state import TradingState
    from reasoning_trading.policy.network import PolicyNetwork
    from reasoning_trading.regime.detector import RegimeDetector


class MCTSOrchestratorConfig(BaseSettings):
    """Configuration for MCTS orchestrator."""

    model_config = SettingsConfigDict(
        env_prefix="MCTS_ORCH_",
        case_sensitive=False,
        extra="ignore",
    )

    # Level-specific iterations
    strategic_iterations: int = Field(
        default=800,
        ge=100,
        le=5000,
        description="Iterations for strategic level",
    )
    tactical_iterations: int = Field(
        default=200,
        ge=50,
        le=1000,
        description="Iterations for tactical level",
    )
    execution_iterations: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Iterations for execution level",
    )

    # Exploration constants per level
    strategic_exploration: float = Field(
        default=2.0,
        ge=0.5,
        le=5.0,
        description="Exploration for strategic level",
    )
    tactical_exploration: float = Field(
        default=1.5,
        ge=0.5,
        le=5.0,
        description="Exploration for tactical level",
    )
    execution_exploration: float = Field(
        default=1.0,
        ge=0.5,
        le=5.0,
        description="Exploration for execution level",
    )

    # Regime adjustments
    high_volatility_exploration_boost: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Extra exploration in high volatility",
    )
    low_volatility_iterations_reduction: float = Field(
        default=0.5,
        ge=0.1,
        le=1.0,
        description="Iteration reduction in low volatility",
    )

    # Timeout settings
    strategic_timeout_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=300.0,
        description="Timeout for strategic search",
    )
    tactical_timeout_seconds: float = Field(
        default=5.0,
        ge=1.0,
        le=60.0,
        description="Timeout for tactical search",
    )
    execution_timeout_seconds: float = Field(
        default=0.5,
        ge=0.1,
        le=5.0,
        description="Timeout for execution search",
    )

    # Parallelism
    parallel_simulations: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Parallel simulations per search",
    )

    # Caching
    enable_result_caching: bool = Field(
        default=True,
        description="Cache search results",
    )
    cache_ttl_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Cache TTL in seconds",
    )


@dataclass
class SearchResult:
    """Result from orchestrated MCTS search."""

    # Primary result
    best_action: str | None
    action_probabilities: dict[str, float]
    value: float
    confidence: float

    # Search metadata
    level: str
    iterations_completed: int
    total_time_ms: float
    tree_size: int

    # Regime context
    regime: str | None = None
    regime_adjusted: bool = False

    # Hierarchical context
    parent_action: str | None = None
    subtask_values: dict[str, float] = field(default_factory=dict)

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "best_action": self.best_action,
            "action_probabilities": self.action_probabilities,
            "value": self.value,
            "confidence": self.confidence,
            "level": self.level,
            "iterations_completed": self.iterations_completed,
            "total_time_ms": self.total_time_ms,
            "tree_size": self.tree_size,
            "regime": self.regime,
            "regime_adjusted": self.regime_adjusted,
            "parent_action": self.parent_action,
            "subtask_values": self.subtask_values,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class HierarchicalSearchResult:
    """Result from hierarchical MCTS search."""

    # Level results
    strategic_result: SearchResult | None = None
    tactical_result: SearchResult | None = None
    execution_result: SearchResult | None = None

    # Overall result
    final_action: str | None = None
    total_time_ms: float = 0.0

    # Success status
    success: bool = True
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategic_result": self.strategic_result.to_dict() if self.strategic_result else None,
            "tactical_result": self.tactical_result.to_dict() if self.tactical_result else None,
            "execution_result": self.execution_result.to_dict() if self.execution_result else None,
            "final_action": self.final_action,
            "total_time_ms": self.total_time_ms,
            "success": self.success,
            "error_message": self.error_message,
        }


class MCTSOrchestrator:
    """
    MCTS Orchestrator using LangGraph supervisor pattern.

    Coordinates MCTS search across hierarchy levels with:
    - Regime-aware configuration
    - Hierarchical decomposition
    - Policy network integration
    - Result caching
    """

    def __init__(
        self,
        config: MCTSOrchestratorConfig | None = None,
        policy_network: PolicyNetwork | None = None,
        regime_detector: RegimeDetector | None = None,
    ):
        """Initialize orchestrator."""
        self.config = config or MCTSOrchestratorConfig()
        self.policy_network = policy_network
        self.regime_detector = regime_detector

        # Create level-specific graphs
        self._graphs: dict[str, MCTSGraph] = {}
        self._create_level_graphs()

        # Result cache
        self._cache: dict[str, tuple[SearchResult, datetime]] = {}

        # Metrics
        self._search_count = 0
        self._total_time_ms = 0.0
        self._cache_hits = 0

    def _create_level_graphs(self) -> None:
        """Create MCTS graphs for each hierarchy level."""
        levels = {
            "strategic": (
                self.config.strategic_iterations,
                self.config.strategic_exploration,
            ),
            "tactical": (
                self.config.tactical_iterations,
                self.config.tactical_exploration,
            ),
            "execution": (
                self.config.execution_iterations,
                self.config.execution_exploration,
            ),
        }

        for level, (iterations, exploration) in levels.items():
            graph_config = MCTSGraphConfig(
                max_iterations=iterations,
                exploration_constant=exploration,
                parallel_simulations=self.config.parallel_simulations,
            )
            node_config = NodeConfig(
                exploration_constant=exploration,
            )

            self._graphs[level] = MCTSGraph(
                config=graph_config,
                node_config=node_config,
                policy_network=self.policy_network,
            )

    async def search(
        self,
        state: TradingState,
        level: str = "tactical",
        parent_action: str | None = None,
    ) -> SearchResult:
        """
        Run MCTS search for the given level.

        Args:
            state: Current trading state
            level: Hierarchy level
            parent_action: Parent action from higher level

        Returns:
            SearchResult with best action and metadata
        """
        start_time = time.perf_counter()

        # Check cache
        cache_key = self._compute_cache_key(state, level, parent_action)
        if self.config.enable_result_caching:
            cached = self._get_cached_result(cache_key)
            if cached is not None:
                self._cache_hits += 1
                return cached

        # Get regime-adjusted configuration
        regime = None
        regime_adjusted = False
        if self.regime_detector is not None:
            try:
                classification = self.regime_detector.detect(state)
                regime = classification.regime
                regime_adjusted = True
            except Exception:
                pass

        # Adjust search parameters based on regime
        iterations, exploration = self._get_regime_adjusted_params(level, regime)

        # Get or create graph
        graph = self._graphs.get(level)
        if graph is None:
            graph = self._graphs["tactical"]

        # Update graph configuration for this search
        graph.config = MCTSGraphConfig(
            max_iterations=iterations,
            exploration_constant=exploration,
            parallel_simulations=self.config.parallel_simulations,
        )

        # Run search with timeout
        timeout = self._get_level_timeout(level)
        try:
            async with asyncio.timeout(timeout):
                features = state.to_feature_vector()
                result = await graph.run(
                    trading_state_features=features,
                    symbol=state.symbol,
                    level=level,
                    max_iterations=iterations,
                )
        except asyncio.TimeoutError:
            # Return partial result
            result = MCTSGraphResult(
                best_action="hold_position",
                action_probabilities={"hold_position": 1.0},
                root_value=0.0,
                iterations_completed=0,
                total_time_ms=timeout * 1000,
                phase_times={},
                tree_size=0,
                success=False,
                error_message="Search timeout",
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Build search result
        search_result = SearchResult(
            best_action=result.best_action,
            action_probabilities=result.action_probabilities,
            value=result.root_value,
            confidence=self._compute_confidence(result),
            level=level,
            iterations_completed=result.iterations_completed,
            total_time_ms=elapsed_ms,
            tree_size=result.tree_size,
            regime=regime,
            regime_adjusted=regime_adjusted,
            parent_action=parent_action,
        )

        # Cache result
        if self.config.enable_result_caching and result.success:
            self._cache_result(cache_key, search_result)

        # Update metrics
        self._search_count += 1
        self._total_time_ms += elapsed_ms

        return search_result

    async def hierarchical_search(
        self,
        state: TradingState,
        target_level: str = "execution",
    ) -> HierarchicalSearchResult:
        """
        Run hierarchical MCTS search from strategic to target level.

        Args:
            state: Current trading state
            target_level: Lowest level to search

        Returns:
            HierarchicalSearchResult with results from all levels
        """
        start_time = time.perf_counter()
        result = HierarchicalSearchResult()

        try:
            # Strategic level
            result.strategic_result = await self.search(state, "strategic")
            strategic_action = result.strategic_result.best_action

            if target_level == "strategic":
                result.final_action = strategic_action
            else:
                # Tactical level (conditioned on strategic)
                result.tactical_result = await self.search(
                    state,
                    "tactical",
                    parent_action=strategic_action,
                )
                tactical_action = result.tactical_result.best_action

                if target_level == "tactical":
                    result.final_action = tactical_action
                else:
                    # Execution level
                    result.execution_result = await self.search(
                        state,
                        "execution",
                        parent_action=tactical_action,
                    )
                    result.final_action = result.execution_result.best_action

            result.success = True

        except Exception as e:
            result.success = False
            result.error_message = str(e)

        result.total_time_ms = (time.perf_counter() - start_time) * 1000

        return result

    async def parallel_search(
        self,
        states: list[TradingState],
        level: str = "tactical",
    ) -> list[SearchResult]:
        """
        Run parallel MCTS searches for multiple states.

        Args:
            states: List of trading states
            level: Hierarchy level

        Returns:
            List of SearchResult objects
        """
        tasks = [self.search(state, level) for state in states]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        search_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                search_results.append(SearchResult(
                    best_action="hold_position",
                    action_probabilities={"hold_position": 1.0},
                    value=0.0,
                    confidence=0.0,
                    level=level,
                    iterations_completed=0,
                    total_time_ms=0.0,
                    tree_size=0,
                ))
            else:
                search_results.append(result)

        return search_results

    def _get_regime_adjusted_params(
        self,
        level: str,
        regime: str | None,
    ) -> tuple[int, float]:
        """Get regime-adjusted search parameters."""
        # Base parameters
        if level == "strategic":
            iterations = self.config.strategic_iterations
            exploration = self.config.strategic_exploration
        elif level == "execution":
            iterations = self.config.execution_iterations
            exploration = self.config.execution_exploration
        else:
            iterations = self.config.tactical_iterations
            exploration = self.config.tactical_exploration

        # Regime adjustments
        if regime == "high_volatility":
            exploration += self.config.high_volatility_exploration_boost
        elif regime == "low_volatility":
            iterations = int(iterations * self.config.low_volatility_iterations_reduction)
            iterations = max(iterations, 10)

        return iterations, exploration

    def _get_level_timeout(self, level: str) -> float:
        """Get timeout for search level."""
        if level == "strategic":
            return self.config.strategic_timeout_seconds
        elif level == "execution":
            return self.config.execution_timeout_seconds
        else:
            return self.config.tactical_timeout_seconds

    def _compute_confidence(self, result: MCTSGraphResult) -> float:
        """Compute confidence score from result."""
        if not result.success:
            return 0.0

        # Based on visit distribution and value
        probs = list(result.action_probabilities.values())
        if not probs:
            return 0.0

        # Confidence from probability concentration
        max_prob = max(probs)
        entropy = -sum(p * np.log(p + 1e-10) for p in probs if p > 0)
        max_entropy = np.log(len(probs)) if len(probs) > 1 else 1.0

        concentration = 1.0 - (entropy / max(max_entropy, 1e-10))

        # Combine with iteration completeness
        iteration_ratio = result.iterations_completed / max(
            self.config.tactical_iterations, 1
        )
        iteration_ratio = min(iteration_ratio, 1.0)

        return 0.5 * max_prob + 0.3 * concentration + 0.2 * iteration_ratio

    def _compute_cache_key(
        self,
        state: TradingState,
        level: str,
        parent_action: str | None,
    ) -> str:
        """Compute cache key for state."""
        import hashlib

        features = state.to_feature_vector()
        discretized = np.round(features, 2)
        feature_hash = hashlib.md5(discretized.tobytes()).hexdigest()[:12]

        return f"{state.symbol}:{level}:{parent_action or 'none'}:{feature_hash}"

    def _get_cached_result(self, key: str) -> SearchResult | None:
        """Get cached result if valid."""
        if key not in self._cache:
            return None

        result, cached_time = self._cache[key]
        elapsed = (datetime.now() - cached_time).total_seconds()

        if elapsed > self.config.cache_ttl_seconds:
            del self._cache[key]
            return None

        return result

    def _cache_result(self, key: str, result: SearchResult) -> None:
        """Cache search result."""
        self._cache[key] = (result, datetime.now())

        # Limit cache size
        max_cache = 1000
        if len(self._cache) > max_cache:
            # Remove oldest entries
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k][1],
            )
            for k in sorted_keys[:len(self._cache) - max_cache]:
                del self._cache[k]

    def get_statistics(self) -> dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "search_count": self._search_count,
            "total_time_ms": self._total_time_ms,
            "avg_time_ms": self._total_time_ms / max(self._search_count, 1),
            "cache_hits": self._cache_hits,
            "cache_hit_rate": self._cache_hits / max(self._search_count, 1),
            "cache_size": len(self._cache),
        }

    def clear_cache(self) -> None:
        """Clear result cache."""
        self._cache.clear()

    def reset_metrics(self) -> None:
        """Reset metrics."""
        self._search_count = 0
        self._total_time_ms = 0.0
        self._cache_hits = 0
