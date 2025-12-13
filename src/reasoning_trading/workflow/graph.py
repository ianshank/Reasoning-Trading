"""
LangGraph workflow for MCTS-enhanced trading decisions.

Implements the complete LangGraph StateGraph that combines:
- MCTS phases (select, expand, simulate, backpropagate)
- Multi-agent trading analysis
- Risk management checks
- Trade execution
"""

from __future__ import annotations

import asyncio
import operator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Any, Literal

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.core.actions import ActionSpace, TradingAction
from reasoning_trading.core.state import TradingState
from reasoning_trading.mcts.node import Node
from reasoning_trading.mcts.rollout import TradingRollout
from reasoning_trading.mcts.tree import MCTSConfig, MCTSResult, MCTSTree
from reasoning_trading.mcts.ucb import SelectionStrategy, create_selector
from reasoning_trading.services.adapter import TradingServiceAdapter

logger = structlog.get_logger(__name__)


class MCTSTradingState(BaseModel):
    """
    State for the MCTS Trading LangGraph workflow.

    This TypedDict-compatible state captures all information needed
    for the trading decision workflow.
    """

    # Input
    symbol: str = ""
    analysis_date: str = ""

    # Conversation history
    messages: Annotated[list[BaseMessage], operator.add] = Field(default_factory=list)

    # MCTS state
    tree_root: Node | None = None
    current_node: Node | None = None
    mcts_result: MCTSResult | None = None

    # Trading state
    trading_state: TradingState | None = None
    portfolio_state: dict[str, Any] = Field(default_factory=dict)

    # Simulation results
    simulation_results: list[dict[str, Any]] = Field(default_factory=list)

    # Decision output
    best_action: TradingAction | None = None
    action_confidence: float = 0.0
    action_reasoning: str = ""

    # Workflow metadata
    iteration_count: int = 0
    max_iterations: int = 1000
    should_continue: bool = True
    error_message: str | None = None

    class Config:
        arbitrary_types_allowed = True


@dataclass
class MCTSTradingGraph:
    """
    MCTS Trading workflow graph manager.

    Manages the LangGraph StateGraph that implements MCTS-based
    trading decision making.
    """

    settings: Settings = field(default_factory=get_settings)
    mcts_config: MCTSConfig = field(default_factory=MCTSConfig)
    trading_adapter: TradingServiceAdapter | None = None
    action_space: ActionSpace = field(default_factory=ActionSpace)

    _graph: StateGraph | None = None
    _compiled_graph: Any = None

    def __post_init__(self) -> None:
        """Initialize the graph after dataclass creation."""
        self.mcts_config = MCTSConfig.from_settings(self.settings.mcts)
        self.action_space = ActionSpace(
            allow_shorts=self.settings.features.allow_shorts,
            max_position_size=self.settings.risk.max_position_size_fraction,
        )

    async def initialize(self) -> None:
        """Initialize async components."""
        if self.trading_adapter is None:
            self.trading_adapter = TradingServiceAdapter(
                mode=self.settings.trading.trading_mode,
                settings=self.settings,
            )
            await self.trading_adapter._initialize()

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.trading_adapter is not None:
            await self.trading_adapter._cleanup()

    def build(self) -> StateGraph:
        """
        Build the MCTS trading workflow graph.

        Returns:
            Configured StateGraph
        """
        workflow = StateGraph(MCTSTradingState)

        # Add nodes for MCTS phases
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("select", self._select_node)
        workflow.add_node("expand", self._expand_node)
        workflow.add_node("simulate", self._simulate_node)
        workflow.add_node("backpropagate", self._backpropagate_node)
        workflow.add_node("decide", self._decide_node)
        workflow.add_node("error_handler", self._error_handler_node)

        # Define edges
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "select")
        workflow.add_edge("select", "expand")
        workflow.add_edge("expand", "simulate")
        workflow.add_edge("simulate", "backpropagate")

        # Conditional edge: continue or decide
        workflow.add_conditional_edges(
            "backpropagate",
            self._should_continue_search,
            {
                "continue": "select",
                "stop": "decide",
                "error": "error_handler",
            },
        )

        workflow.add_edge("decide", END)
        workflow.add_edge("error_handler", END)

        self._graph = workflow
        self._compiled_graph = workflow.compile()

        return workflow

    def compile(self) -> Any:
        """Compile the graph for execution."""
        if self._compiled_graph is None:
            self.build()
        return self._compiled_graph

    async def run(
        self,
        symbol: str,
        analysis_date: str | None = None,
    ) -> MCTSTradingState:
        """
        Run the MCTS trading workflow.

        Args:
            symbol: Trading symbol to analyze
            analysis_date: Date for analysis (defaults to today)

        Returns:
            Final MCTSTradingState with trading decision
        """
        if self._compiled_graph is None:
            self.build()

        await self.initialize()

        if analysis_date is None:
            analysis_date = datetime.now().strftime("%Y-%m-%d")

        initial_state = MCTSTradingState(
            symbol=symbol,
            analysis_date=analysis_date,
            max_iterations=self.mcts_config.max_simulations,
        )

        logger.info(
            "Starting MCTS trading workflow",
            symbol=symbol,
            date=analysis_date,
        )

        try:
            final_state = await self._compiled_graph.ainvoke(initial_state)
            return MCTSTradingState(**final_state)
        except Exception as e:
            logger.error("Workflow failed", error=str(e))
            initial_state.error_message = str(e)
            return initial_state

    async def _initialize_node(self, state: MCTSTradingState) -> dict[str, Any]:
        """
        Initialize the MCTS search.

        Fetches trading state and creates root node.
        """
        try:
            # Build trading state
            trading_state = await self.trading_adapter.build_trading_state(state.symbol)

            # Create root node
            root = Node(state=trading_state)

            # Get portfolio state
            portfolio = await self.trading_adapter.get_portfolio_state()

            return {
                "trading_state": trading_state,
                "tree_root": root,
                "current_node": root,
                "portfolio_state": portfolio.model_dump(),
                "messages": [
                    HumanMessage(
                        content=f"Analyzing {state.symbol} for trading decision on {state.analysis_date}"
                    )
                ],
            }

        except Exception as e:
            logger.error("Initialization failed", error=str(e))
            return {"error_message": str(e), "should_continue": False}

    async def _select_node(self, state: MCTSTradingState) -> dict[str, Any]:
        """
        UCB-based node selection phase.

        Traverses from root to a leaf using UCB selection.
        """
        if state.tree_root is None:
            return {"error_message": "No tree root", "should_continue": False}

        selector = create_selector(
            self.mcts_config.selection_strategy,
            exploration_constant=self.mcts_config.exploration_weight,
        )

        # Select from root to leaf
        current = state.tree_root
        depth = 0

        while not current.is_leaf and depth < self.mcts_config.max_depth:
            selected = selector.select(current)
            if selected is None:
                break
            current = selected
            depth += 1

        return {
            "current_node": current,
            "iteration_count": state.iteration_count + 1,
        }

    async def _expand_node(self, state: MCTSTradingState) -> dict[str, Any]:
        """
        Node expansion phase.

        Generates new child nodes using progressive widening.
        """
        if state.current_node is None or state.current_node.state is None:
            return {"error_message": "Invalid current node", "should_continue": False}

        node = state.current_node

        # Get existing actions
        existing_actions = [c.action for c in node.children if c.action is not None]

        # Get candidate actions via progressive widening
        candidates = self.action_space.get_candidate_actions(
            visit_count=max(node.visits, 1),
            existing_actions=existing_actions,
        )

        if not candidates:
            # No new actions to expand
            return {}

        # Expand first candidate
        action = candidates[0]

        # Create new state by applying action
        new_trading_state = node.state.copy()
        new_trading_state.simulation_step += 1

        # Create child node
        child = node.expand(
            action=action,
            new_state=new_trading_state,
            prior=action.confidence,
        )

        return {"current_node": child}

    async def _simulate_node(self, state: MCTSTradingState) -> dict[str, Any]:
        """
        Simulation (rollout) phase.

        Runs trading simulation to estimate node value.
        """
        if state.current_node is None:
            return {"error_message": "No current node", "should_continue": False}

        rollout_engine = TradingRollout(
            horizon_days=self.mcts_config.rollout_horizon,
            discount_factor=self.mcts_config.discount_factor,
        )

        try:
            async with asyncio.timeout(
                self.mcts_config.per_simulation_timeout_ms / 1000
            ):
                value = await rollout_engine.rollout(
                    state.current_node,
                    depth=self.mcts_config.rollout_horizon,
                )

            result = {
                "node_id": state.current_node.id,
                "value": value,
                "depth": state.current_node.depth,
                "action": state.current_node.action.to_dict() if state.current_node.action else None,
            }

            return {
                "simulation_results": [result],
                "current_node": state.current_node,
            }

        except asyncio.TimeoutError:
            logger.warning("Simulation timeout")
            return {"simulation_results": [{"value": 0.0, "timeout": True}]}
        except Exception as e:
            logger.error("Simulation failed", error=str(e))
            return {"error_message": str(e), "should_continue": False}

    async def _backpropagate_node(self, state: MCTSTradingState) -> dict[str, Any]:
        """
        Backpropagation phase.

        Updates node statistics from leaf to root.
        """
        if state.current_node is None or not state.simulation_results:
            return {}

        # Get most recent simulation value
        latest_result = state.simulation_results[-1]
        value = latest_result.get("value", 0.0)

        # Backpropagate
        state.current_node.backpropagate(
            value,
            discount=self.mcts_config.discount_factor,
        )

        return {"tree_root": state.tree_root}

    def _should_continue_search(
        self, state: MCTSTradingState
    ) -> Literal["continue", "stop", "error"]:
        """
        Determine if search should continue.

        Checks iteration count, confidence threshold, and errors.
        """
        if state.error_message:
            return "error"

        if not state.should_continue:
            return "stop"

        if state.iteration_count >= state.max_iterations:
            logger.info("Max iterations reached", count=state.iteration_count)
            return "stop"

        # Check confidence threshold
        if state.tree_root and len(state.tree_root.children) >= 2:
            sorted_children = sorted(
                state.tree_root.children,
                key=lambda c: c.visits,
                reverse=True,
            )
            best = sorted_children[0]
            second = sorted_children[1]

            if best.visits > 0 and second.visits > 0:
                visit_ratio = best.visits / (best.visits + second.visits)
                if visit_ratio > self.mcts_config.confidence_threshold:
                    logger.info(
                        "Early termination due to confidence",
                        ratio=visit_ratio,
                    )
                    return "stop"

        return "continue"

    async def _decide_node(self, state: MCTSTradingState) -> dict[str, Any]:
        """
        Final decision phase.

        Extracts best action from tree and generates reasoning.
        """
        if state.tree_root is None:
            return {
                "best_action": TradingAction.hold(),
                "action_confidence": 0.0,
                "action_reasoning": "No tree root available",
            }

        # Get best child by visit count
        best_child = state.tree_root.best_action_child()

        if best_child is None or best_child.action is None:
            return {
                "best_action": TradingAction.hold(),
                "action_confidence": 0.0,
                "action_reasoning": "No valid actions found",
            }

        # Calculate confidence
        total_visits = sum(c.visits for c in state.tree_root.children)
        confidence = best_child.visits / total_visits if total_visits > 0 else 0.0

        # Build reasoning
        reasoning = self._build_decision_reasoning(state, best_child)

        # Build MCTS result
        mcts_result = MCTSResult(
            best_action=best_child.action,
            best_node=best_child,
            root=state.tree_root,
            total_simulations=state.iteration_count,
            best_value=best_child.mean_value,
            best_visits=best_child.visits,
        )

        return {
            "best_action": best_child.action,
            "action_confidence": confidence,
            "action_reasoning": reasoning,
            "mcts_result": mcts_result,
            "messages": [
                AIMessage(content=f"Decision: {best_child.action.direction.value}\n{reasoning}")
            ],
        }

    async def _error_handler_node(self, state: MCTSTradingState) -> dict[str, Any]:
        """
        Handle errors in the workflow.
        """
        logger.error("Workflow error", error=state.error_message)

        return {
            "best_action": TradingAction.hold(),
            "action_confidence": 0.0,
            "action_reasoning": f"Error occurred: {state.error_message}",
            "messages": [
                AIMessage(content=f"Error: {state.error_message}. Defaulting to HOLD.")
            ],
        }

    def _build_decision_reasoning(
        self,
        state: MCTSTradingState,
        best_child: Node,
    ) -> str:
        """Build human-readable reasoning for the decision."""
        lines = [
            f"MCTS Analysis for {state.symbol}",
            f"Date: {state.analysis_date}",
            "",
            f"Best Action: {best_child.action.direction.value.upper()}",
            f"Position Size: {best_child.action.position_size.size_fraction:.1%}",
            f"Stop Loss: {best_child.action.stop_loss.stop_loss_pct:.1%}",
            f"Time Horizon: {best_child.action.time_horizon.value}",
            "",
            "MCTS Statistics:",
            f"  - Total Simulations: {state.iteration_count}",
            f"  - Best Node Visits: {best_child.visits}",
            f"  - Best Node Value: {best_child.mean_value:.4f}",
            "",
        ]

        # Add action distribution
        if state.tree_root and state.tree_root.children:
            lines.append("Action Distribution:")
            total_visits = sum(c.visits for c in state.tree_root.children)
            for child in sorted(
                state.tree_root.children, key=lambda c: c.visits, reverse=True
            )[:5]:
                if child.action and child.visits > 0:
                    pct = child.visits / total_visits * 100
                    lines.append(
                        f"  - {child.action.direction.value}: "
                        f"{pct:.1f}% (value: {child.mean_value:.4f})"
                    )

        # Add analyst signals if available
        if state.trading_state:
            signals = state.trading_state.analyst_signals
            lines.extend([
                "",
                "Analyst Signals:",
                f"  - Market: {signals.market_analyst_score:.2f}",
                f"  - News: {signals.news_analyst_score:.2f}",
                f"  - Social: {signals.social_sentiment_score:.2f}",
                f"  - Fundamental: {signals.fundamental_analyst_score:.2f}",
                f"  - Macro: {signals.macro_analyst_score:.2f}",
                f"  - Consensus: {signals.researcher_consensus:.2f}",
            ])

        return "\n".join(lines)


def build_trading_mcts_graph(
    settings: Settings | None = None,
) -> MCTSTradingGraph:
    """
    Factory function to build the trading MCTS graph.

    Args:
        settings: Application settings (uses defaults if not provided)

    Returns:
        Configured MCTSTradingGraph
    """
    settings = settings or get_settings()
    graph = MCTSTradingGraph(settings=settings)
    graph.build()
    return graph
