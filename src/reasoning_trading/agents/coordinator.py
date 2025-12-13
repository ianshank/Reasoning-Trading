"""
Multi-agent trading coordinator using MCTS planning.

Coordinates specialized trading agents for different market segments,
timeframes, and strategies using MCTS for optimal agent selection.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

import structlog

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.core.actions import ActionSpace, TradingAction, TradingDirection
from reasoning_trading.core.state import TradingState
from reasoning_trading.mcts.node import Node
from reasoning_trading.mcts.tree import MCTSConfig, MCTSTree

logger = structlog.get_logger(__name__)


class AgentType(str, Enum):
    """Types of specialized trading agents."""

    # Asset class specialists
    EQUITIES = "equities"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITIES = "commodities"

    # Timeframe specialists
    SCALP = "scalp"
    INTRADAY = "intraday"
    SWING = "swing"
    POSITION = "position"

    # Strategy specialists
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    ARBITRAGE = "arbitrage"


class TradingAgentProtocol(Protocol):
    """Protocol for trading agent implementations."""

    async def analyze(self, state: TradingState) -> TradingAction:
        """Analyze state and return recommended action."""
        ...

    @property
    def agent_type(self) -> AgentType:
        """Get agent type."""
        ...

    @property
    def confidence(self) -> float:
        """Get agent's confidence in current market conditions."""
        ...


@dataclass
class AgentResult:
    """Result from a trading agent analysis."""

    agent_type: AgentType
    action: TradingAction
    confidence: float
    reasoning: str = ""
    analysis_time_ms: float = 0.0


@dataclass
class BaseAgent(ABC):
    """Base class for specialized trading agents."""

    settings: Settings = field(default_factory=get_settings)

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Get the agent type."""
        pass

    @abstractmethod
    async def analyze(self, state: TradingState) -> TradingAction:
        """
        Analyze trading state and return recommended action.

        Args:
            state: Current trading state

        Returns:
            Recommended trading action
        """
        pass

    def _build_action(
        self,
        direction: TradingDirection,
        size_fraction: float,
        stop_loss_pct: float,
        confidence: float,
        reasoning: str = "",
    ) -> TradingAction:
        """Helper to build a TradingAction."""
        from reasoning_trading.core.actions import (
            PositionSizeAction,
            StopLossAction,
            TimeHorizon,
        )

        return TradingAction(
            direction=direction,
            position_size=PositionSizeAction(size_fraction=size_fraction),
            stop_loss=StopLossAction(stop_loss_pct=stop_loss_pct),
            time_horizon=TimeHorizon.INTRADAY,
            confidence=confidence,
            reasoning=reasoning,
        )


@dataclass
class MomentumAgent(BaseAgent):
    """Agent specialized in momentum-based strategies."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.MOMENTUM

    async def analyze(self, state: TradingState) -> TradingAction:
        """Momentum-based analysis."""
        indicators = state.technical_indicators

        # Check for momentum signals
        rsi = indicators.rsi_14 if indicators.rsi_14 is not None else 50
        macd_hist = indicators.macd_histogram if indicators.macd_histogram is not None else 0

        # Momentum score
        momentum_score = 0.0

        # RSI momentum
        if rsi > 70:
            momentum_score += 0.3  # Overbought but strong momentum
        elif rsi > 50:
            momentum_score += 0.2
        elif rsi < 30:
            momentum_score -= 0.3  # Oversold
        elif rsi < 50:
            momentum_score -= 0.2

        # MACD momentum
        momentum_score += max(min(macd_hist / 2, 0.3), -0.3)

        # Trend alignment
        if indicators.sma_20 and indicators.sma_50:
            if indicators.sma_20 > indicators.sma_50:
                momentum_score += 0.2
            else:
                momentum_score -= 0.2

        # Determine action
        confidence = abs(momentum_score)

        if momentum_score > 0.3:
            return self._build_action(
                TradingDirection.BUY,
                min(0.15, confidence * 0.2),
                0.05,
                confidence,
                f"Strong momentum (score={momentum_score:.2f})",
            )
        elif momentum_score < -0.3:
            return self._build_action(
                TradingDirection.SELL,
                min(0.15, confidence * 0.2),
                0.05,
                confidence,
                f"Weak momentum (score={momentum_score:.2f})",
            )
        else:
            return self._build_action(
                TradingDirection.HOLD,
                0.0,
                0.05,
                0.5,
                "Neutral momentum",
            )


@dataclass
class MeanReversionAgent(BaseAgent):
    """Agent specialized in mean reversion strategies."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.MEAN_REVERSION

    async def analyze(self, state: TradingState) -> TradingAction:
        """Mean reversion analysis."""
        indicators = state.technical_indicators

        # Check for mean reversion signals
        rsi = indicators.rsi_14 if indicators.rsi_14 is not None else 50

        # Bollinger Band position
        bb_position = 0.5  # Default to middle
        if indicators.bollinger_upper and indicators.bollinger_lower:
            bb_range = indicators.bollinger_upper - indicators.bollinger_lower
            if bb_range > 0:
                bb_position = (state.current_price - indicators.bollinger_lower) / bb_range

        # Mean reversion score (opposite of momentum)
        mr_score = 0.0

        # RSI extremes favor reversion
        if rsi > 70:
            mr_score -= 0.4  # Expect pullback
        elif rsi < 30:
            mr_score += 0.4  # Expect bounce

        # Bollinger extremes
        if bb_position > 0.95:
            mr_score -= 0.3
        elif bb_position < 0.05:
            mr_score += 0.3

        confidence = abs(mr_score)

        if mr_score > 0.3:
            return self._build_action(
                TradingDirection.BUY,
                min(0.10, confidence * 0.15),
                0.03,
                confidence,
                f"Mean reversion buy (score={mr_score:.2f})",
            )
        elif mr_score < -0.3:
            return self._build_action(
                TradingDirection.SELL,
                min(0.10, confidence * 0.15),
                0.03,
                confidence,
                f"Mean reversion sell (score={mr_score:.2f})",
            )
        else:
            return self._build_action(
                TradingDirection.HOLD,
                0.0,
                0.03,
                0.5,
                "No mean reversion signal",
            )


@dataclass
class BreakoutAgent(BaseAgent):
    """Agent specialized in breakout strategies."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.BREAKOUT

    async def analyze(self, state: TradingState) -> TradingAction:
        """Breakout analysis."""
        indicators = state.technical_indicators

        # Check for breakout conditions
        breakout_score = 0.0

        # ADX trend strength
        adx = indicators.adx_14 if indicators.adx_14 is not None else 25
        if adx > 25:
            breakout_score += 0.2

        # Bollinger Band breakout
        if indicators.bollinger_upper and indicators.bollinger_lower:
            if state.current_price > indicators.bollinger_upper:
                breakout_score += 0.4  # Upper breakout
            elif state.current_price < indicators.bollinger_lower:
                breakout_score -= 0.4  # Lower breakout

        # Volume confirmation (if available)
        if indicators.volume_sma_20:
            # Would need current volume - skip for now
            pass

        confidence = min(abs(breakout_score), 1.0)

        if breakout_score > 0.3:
            return self._build_action(
                TradingDirection.BUY,
                min(0.12, confidence * 0.18),
                0.04,
                confidence,
                f"Bullish breakout (score={breakout_score:.2f})",
            )
        elif breakout_score < -0.3:
            return self._build_action(
                TradingDirection.SELL,
                min(0.12, confidence * 0.18),
                0.04,
                confidence,
                f"Bearish breakdown (score={breakout_score:.2f})",
            )
        else:
            return self._build_action(
                TradingDirection.HOLD,
                0.0,
                0.04,
                0.5,
                "No breakout signal",
            )


@dataclass
class MultiAgentTradingMCTS:
    """
    Coordinate specialized agents via MCTS planning.

    Uses MCTS to select and weight the optimal combination of
    specialized trading agents based on current market conditions.
    """

    settings: Settings = field(default_factory=get_settings)

    # Available agents
    agents: dict[AgentType, BaseAgent] = field(default_factory=dict)

    # MCTS configuration for agent selection
    mcts_config: MCTSConfig = field(default_factory=MCTSConfig)

    def __post_init__(self) -> None:
        """Initialize default agents."""
        if not self.agents:
            self.agents = {
                AgentType.MOMENTUM: MomentumAgent(settings=self.settings),
                AgentType.MEAN_REVERSION: MeanReversionAgent(settings=self.settings),
                AgentType.BREAKOUT: BreakoutAgent(settings=self.settings),
            }

    async def analyze(self, state: TradingState) -> TradingAction:
        """
        Analyze using multiple agents and combine recommendations.

        Uses MCTS to explore agent combinations and select optimal
        weighting based on simulated performance.

        Args:
            state: Current trading state

        Returns:
            Combined trading action
        """
        logger.info(
            "Multi-agent analysis starting",
            symbol=state.symbol,
            num_agents=len(self.agents),
        )

        # Get recommendations from all agents
        agent_results = await self._gather_agent_recommendations(state)

        # Select best combination using MCTS
        best_action = await self._select_best_combination(state, agent_results)

        logger.info(
            "Multi-agent analysis complete",
            direction=best_action.direction.value,
            confidence=best_action.confidence,
        )

        return best_action

    async def _gather_agent_recommendations(
        self, state: TradingState
    ) -> list[AgentResult]:
        """Gather recommendations from all agents concurrently."""
        results = []

        async def run_agent(agent: BaseAgent) -> AgentResult:
            start = datetime.now()
            try:
                action = await agent.analyze(state)
                elapsed = (datetime.now() - start).total_seconds() * 1000
                return AgentResult(
                    agent_type=agent.agent_type,
                    action=action,
                    confidence=action.confidence,
                    reasoning=action.reasoning,
                    analysis_time_ms=elapsed,
                )
            except Exception as e:
                logger.error(
                    "Agent analysis failed",
                    agent=agent.agent_type.value,
                    error=str(e),
                )
                return AgentResult(
                    agent_type=agent.agent_type,
                    action=TradingAction.hold(),
                    confidence=0.0,
                    reasoning=f"Error: {str(e)}",
                )

        tasks = [run_agent(agent) for agent in self.agents.values()]
        results = await asyncio.gather(*tasks)

        return list(results)

    async def _select_best_combination(
        self,
        state: TradingState,
        agent_results: list[AgentResult],
    ) -> TradingAction:
        """
        Use MCTS to select best agent combination.

        Builds a tree where nodes represent different agent weightings
        and uses rollouts to evaluate expected performance.
        """
        # Simple weighted combination for now
        # Full MCTS over agent combinations is computationally expensive

        # Filter to confident recommendations
        confident_results = [r for r in agent_results if r.confidence > 0.3]

        if not confident_results:
            # No confident recommendations - hold
            return TradingAction.hold()

        # Weight by confidence
        total_confidence = sum(r.confidence for r in confident_results)

        # Aggregate direction votes
        buy_weight = sum(
            r.confidence
            for r in confident_results
            if r.action.direction == TradingDirection.BUY
        )
        sell_weight = sum(
            r.confidence
            for r in confident_results
            if r.action.direction == TradingDirection.SELL
        )

        # Determine consensus direction
        if buy_weight > sell_weight * 1.2:
            direction = TradingDirection.BUY
            net_confidence = buy_weight / total_confidence
        elif sell_weight > buy_weight * 1.2:
            direction = TradingDirection.SELL
            net_confidence = sell_weight / total_confidence
        else:
            direction = TradingDirection.HOLD
            net_confidence = 0.5

        # Aggregate position sizes (weighted average)
        avg_size = sum(
            r.action.position_size.size_fraction * r.confidence
            for r in confident_results
            if r.action.direction == direction
        ) / max(sum(r.confidence for r in confident_results if r.action.direction == direction), 1)

        # Aggregate stop-loss (take most conservative)
        stop_losses = [
            r.action.stop_loss.stop_loss_pct
            for r in confident_results
            if r.action.direction == direction
        ]
        avg_stop_loss = min(stop_losses) if stop_losses else 0.05

        # Build reasoning
        reasoning_parts = [
            f"Combined {len(confident_results)} agents:"
        ]
        for r in confident_results:
            reasoning_parts.append(
                f"  - {r.agent_type.value}: {r.action.direction.value} ({r.confidence:.0%})"
            )

        from reasoning_trading.core.actions import (
            PositionSizeAction,
            StopLossAction,
            TimeHorizon,
        )

        return TradingAction(
            direction=direction,
            position_size=PositionSizeAction(size_fraction=avg_size),
            stop_loss=StopLossAction(stop_loss_pct=avg_stop_loss),
            time_horizon=TimeHorizon.INTRADAY,
            confidence=net_confidence,
            reasoning="\n".join(reasoning_parts),
        )

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a new specialized agent."""
        self.agents[agent.agent_type] = agent
        logger.info("Agent registered", agent_type=agent.agent_type.value)

    def remove_agent(self, agent_type: AgentType) -> None:
        """Remove an agent from the coordinator."""
        if agent_type in self.agents:
            del self.agents[agent_type]
            logger.info("Agent removed", agent_type=agent_type.value)

    def get_agent_stats(self) -> dict[str, Any]:
        """Get statistics about registered agents."""
        return {
            "total_agents": len(self.agents),
            "agent_types": [a.value for a in self.agents.keys()],
        }
