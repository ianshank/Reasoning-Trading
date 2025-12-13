"""
Batch Layer for Lambda Architecture.

Handles computationally intensive overnight strategic planning:
- Deep hierarchical MCTS for portfolio allocation
- Policy precomputation for anticipated market states
- Model retraining on accumulated trading data
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from reasoning_trading.core.state import TradingState
    from reasoning_trading.hierarchical.tree import HierarchicalMCTSTree, HierarchicalMCTSResult


class BatchJobStatus(str, Enum):
    """Status of a batch job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchJobType(str, Enum):
    """Types of batch jobs."""

    STRATEGIC_MCTS = "strategic_mcts"
    POLICY_PRECOMPUTE = "policy_precompute"
    MODEL_RETRAIN = "model_retrain"
    REGIME_ANALYSIS = "regime_analysis"


class BatchLayerConfig(BaseSettings):
    """Configuration for batch layer."""

    model_config = SettingsConfigDict(
        env_prefix="BATCH_",
        case_sensitive=False,
        extra="ignore",
    )

    # MCTS configuration
    strategic_simulations: int = Field(
        default=5000,
        ge=100,
        le=100000,
        description="Simulations for strategic MCTS",
    )
    symbols_per_batch: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Symbols to analyze per batch",
    )
    max_concurrent_jobs: int = Field(
        default=4,
        ge=1,
        le=64,
        description="Maximum concurrent batch jobs",
    )

    # Timing
    batch_start_hour: int = Field(
        default=22,
        ge=0,
        le=23,
        description="Hour to start batch processing (UTC)",
    )
    max_batch_duration_hours: int = Field(
        default=6,
        ge=1,
        le=12,
        description="Maximum batch processing duration",
    )

    # Policy precomputation
    precompute_regimes: list[str] = Field(
        default=["trending_up", "trending_down", "volatile", "mean_reverting"],
        description="Regimes to precompute policies for",
    )
    states_per_regime: int = Field(
        default=100,
        ge=10,
        le=10000,
        description="States to precompute per regime",
    )

    # Model retraining
    retrain_frequency_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Days between model retraining",
    )
    min_samples_for_retrain: int = Field(
        default=1000,
        ge=100,
        le=100000,
        description="Minimum samples needed for retraining",
    )


@dataclass
class BatchJob:
    """Represents a batch processing job."""

    id: str = field(default_factory=lambda: str(uuid4()))
    job_type: BatchJobType = BatchJobType.STRATEGIC_MCTS
    status: BatchJobStatus = BatchJobStatus.PENDING

    # Job parameters
    symbols: list[str] = field(default_factory=list)
    regime: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Results
    results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Get job duration in seconds."""
        if self.started_at is None:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "job_type": self.job_type.value,
            "status": self.status.value,
            "symbols": self.symbols,
            "regime": self.regime,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


@dataclass
class BatchResult:
    """Result of batch processing."""

    job_id: str
    job_type: BatchJobType

    # Strategic MCTS results
    strategic_policies: dict[str, dict[str, float]] = field(default_factory=dict)
    strategic_values: dict[str, float] = field(default_factory=dict)

    # Precomputed policies
    precomputed_policies: dict[str, dict[str, float]] = field(default_factory=dict)

    # Statistics
    total_simulations: int = 0
    total_time_seconds: float = 0.0
    symbols_processed: int = 0

    # Quality metrics
    avg_confidence: float = 0.0
    coverage_pct: float = 0.0

    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type.value,
            "strategic_policies": self.strategic_policies,
            "strategic_values": self.strategic_values,
            "total_simulations": self.total_simulations,
            "total_time_seconds": self.total_time_seconds,
            "symbols_processed": self.symbols_processed,
            "avg_confidence": self.avg_confidence,
            "coverage_pct": self.coverage_pct,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class BatchLayer:
    """
    Batch Layer for overnight strategic planning.

    Responsibilities:
    - Deep hierarchical MCTS for portfolio allocation
    - Precompute policy distributions for anticipated states
    - Retrain distilled policy networks
    """

    def __init__(
        self,
        config: BatchLayerConfig | None = None,
        mcts_tree: HierarchicalMCTSTree | None = None,
    ):
        """Initialize batch layer."""
        self.config = config or BatchLayerConfig()
        self.mcts_tree = mcts_tree

        # Job management
        self._pending_jobs: list[BatchJob] = []
        self._running_jobs: dict[str, BatchJob] = {}
        self._completed_jobs: list[BatchJob] = []

        # Results cache
        self._results: dict[str, BatchResult] = {}

        # State
        self._is_running = False
        self._last_batch_time: datetime | None = None

    async def submit_job(self, job: BatchJob) -> str:
        """
        Submit a batch job for processing.

        Args:
            job: BatchJob to submit

        Returns:
            Job ID
        """
        job.status = BatchJobStatus.PENDING
        self._pending_jobs.append(job)
        return job.id

    async def run_strategic_mcts(
        self,
        states: dict[str, TradingState],
    ) -> BatchResult:
        """
        Run strategic MCTS for multiple symbols.

        Args:
            states: Dictionary mapping symbols to trading states

        Returns:
            BatchResult with policies and values
        """
        import time

        job = BatchJob(
            job_type=BatchJobType.STRATEGIC_MCTS,
            symbols=list(states.keys()),
        )
        job.status = BatchJobStatus.RUNNING
        job.started_at = datetime.now()

        result = BatchResult(
            job_id=job.id,
            job_type=BatchJobType.STRATEGIC_MCTS,
        )

        start_time = time.time()
        total_sims = 0

        try:
            for symbol, state in states.items():
                if self.mcts_tree is not None:
                    # Run hierarchical MCTS
                    mcts_result = await self.mcts_tree.search(state)

                    # Extract policy distribution
                    policy = {}
                    if mcts_result.root is not None:
                        policy = self.mcts_tree.get_action_distribution("strategic")

                    result.strategic_policies[symbol] = policy
                    result.strategic_values[symbol] = mcts_result.strategic_value
                    total_sims += mcts_result.total_simulations
                else:
                    # Fallback: heuristic policy
                    consensus = state.analyst_signals.weighted_consensus()
                    if consensus > 0.3:
                        policy = {"increase_equity_allocation": 0.6, "maintain_allocation": 0.4}
                    elif consensus < -0.3:
                        policy = {"decrease_equity_allocation": 0.6, "maintain_allocation": 0.4}
                    else:
                        policy = {"maintain_allocation": 0.8, "rebalance_sectors": 0.2}

                    result.strategic_policies[symbol] = policy
                    result.strategic_values[symbol] = consensus

            result.total_simulations = total_sims
            result.total_time_seconds = time.time() - start_time
            result.symbols_processed = len(states)

            # Calculate confidence
            if result.strategic_policies:
                confidences = [
                    max(p.values()) if p else 0
                    for p in result.strategic_policies.values()
                ]
                result.avg_confidence = np.mean(confidences) if confidences else 0

            # Set expiration
            result.expires_at = datetime.now() + timedelta(hours=24)

            job.status = BatchJobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.results = result.to_dict()

        except Exception as e:
            job.status = BatchJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now()

        self._completed_jobs.append(job)
        self._results[job.id] = result

        return result

    async def precompute_policies(
        self,
        state_generator: Any,
        regimes: list[str] | None = None,
    ) -> BatchResult:
        """
        Precompute policies for anticipated market states.

        Args:
            state_generator: Generator that produces (regime, state) tuples
            regimes: Optional list of regimes to process

        Returns:
            BatchResult with precomputed policies
        """
        import time

        regimes = regimes or self.config.precompute_regimes

        job = BatchJob(
            job_type=BatchJobType.POLICY_PRECOMPUTE,
            parameters={"regimes": regimes},
        )
        job.status = BatchJobStatus.RUNNING
        job.started_at = datetime.now()

        result = BatchResult(
            job_id=job.id,
            job_type=BatchJobType.POLICY_PRECOMPUTE,
        )

        start_time = time.time()
        total_sims = 0

        try:
            for regime in regimes:
                # Generate states for this regime
                states = state_generator(regime, self.config.states_per_regime)

                for state in states:
                    state_hash = self._compute_state_hash(state)

                    if self.mcts_tree is not None:
                        mcts_result = await self.mcts_tree.search(state)
                        policy = self.mcts_tree.get_action_distribution("strategic")
                        total_sims += mcts_result.total_simulations
                    else:
                        # Heuristic policy based on regime
                        if regime == "trending_up":
                            policy = {"increase_equity_allocation": 0.7, "maintain_allocation": 0.3}
                        elif regime == "trending_down":
                            policy = {"decrease_equity_allocation": 0.7, "increase_cash": 0.3}
                        elif regime == "volatile":
                            policy = {"decrease_equity_allocation": 0.4, "increase_cash": 0.6}
                        else:
                            policy = {"maintain_allocation": 0.6, "rebalance_sectors": 0.4}

                    result.precomputed_policies[f"{regime}:{state_hash}"] = policy

            result.total_simulations = total_sims
            result.total_time_seconds = time.time() - start_time
            result.coverage_pct = len(result.precomputed_policies) / (
                len(regimes) * self.config.states_per_regime
            ) * 100

            result.expires_at = datetime.now() + timedelta(hours=24)

            job.status = BatchJobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.results = result.to_dict()

        except Exception as e:
            job.status = BatchJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now()

        self._completed_jobs.append(job)
        self._results[job.id] = result

        return result

    def get_result(self, job_id: str) -> BatchResult | None:
        """Get result for a job."""
        return self._results.get(job_id)

    def get_job_status(self, job_id: str) -> BatchJobStatus | None:
        """Get status of a job."""
        # Check running jobs
        if job_id in self._running_jobs:
            return self._running_jobs[job_id].status

        # Check completed jobs
        for job in self._completed_jobs:
            if job.id == job_id:
                return job.status

        # Check pending jobs
        for job in self._pending_jobs:
            if job.id == job_id:
                return job.status

        return None

    def get_latest_result(
        self,
        job_type: BatchJobType | None = None,
    ) -> BatchResult | None:
        """Get most recent result, optionally filtered by type."""
        matching_results = [
            r for r in self._results.values()
            if job_type is None or r.job_type == job_type
        ]

        if not matching_results:
            return None

        return max(matching_results, key=lambda r: r.created_at)

    def _compute_state_hash(self, state: TradingState) -> str:
        """Compute hash for state caching."""
        import hashlib

        features = state.to_feature_vector()
        discretized = np.round(features, 2)
        return hashlib.md5(discretized.tobytes()).hexdigest()[:16]

    async def run_batch_cycle(self) -> list[BatchResult]:
        """
        Run a complete batch processing cycle.

        Returns:
            List of batch results
        """
        self._is_running = True
        self._last_batch_time = datetime.now()

        results = []

        try:
            # Process pending jobs
            while self._pending_jobs and len(self._running_jobs) < self.config.max_concurrent_jobs:
                job = self._pending_jobs.pop(0)
                self._running_jobs[job.id] = job

                if job.job_type == BatchJobType.STRATEGIC_MCTS:
                    # Would need to reconstruct states from symbols
                    pass
                elif job.job_type == BatchJobType.POLICY_PRECOMPUTE:
                    # Would need state generator
                    pass

        finally:
            self._is_running = False

        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get batch layer statistics."""
        return {
            "is_running": self._is_running,
            "pending_jobs": len(self._pending_jobs),
            "running_jobs": len(self._running_jobs),
            "completed_jobs": len(self._completed_jobs),
            "total_results": len(self._results),
            "last_batch_time": self._last_batch_time.isoformat() if self._last_batch_time else None,
        }
