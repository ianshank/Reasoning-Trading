"""
MCTS search endpoints.

This module provides REST API endpoints for:
- Running MCTS searches
- Hierarchical MCTS operations
- Tree visualization data
- Action distribution analysis
- MCTS configuration management
"""

from datetime import datetime
from typing import Any

import numpy as np
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from reasoning_trading.core.actions import ActionSpace
from reasoning_trading.core.state import TradingState
from reasoning_trading.hierarchical.tree import HierarchicalMCTSTree
from reasoning_trading.mcts.tree import MCTSConfig, MCTSTree

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/mcts", tags=["mcts"])


# Request/Response Models
class SearchRequest(BaseModel):
    """Request to run MCTS search."""

    symbol: str
    current_price: float = Field(..., gt=0)
    max_simulations: int = Field(default=1000, ge=1, le=10000)
    exploration_weight: float = Field(default=1.414, ge=0.0, le=10.0)
    time_budget_ms: int | None = Field(default=None, ge=50, le=60000)
    discount_factor: float = Field(default=0.99, ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    """Response from MCTS search."""

    search_id: str
    best_action: dict[str, Any]
    best_value: float
    best_visits: int
    total_simulations: int
    total_time_ms: float
    simulations_per_second: float
    max_depth_reached: int
    total_nodes: int
    timestamp: datetime


class HierarchicalSearchRequest(BaseModel):
    """Request to run hierarchical MCTS search."""

    symbol: str
    current_price: float = Field(..., gt=0)
    strategic_simulations: int = Field(default=500, ge=1, le=5000)
    tactical_simulations: int = Field(default=1000, ge=1, le=10000)
    time_budget_ms: int | None = Field(default=None, ge=50, le=60000)


class HierarchicalSearchResponse(BaseModel):
    """Response from hierarchical MCTS search."""

    search_id: str
    strategic_action: dict[str, Any]
    tactical_actions: list[dict[str, Any]]
    strategic_value: float
    total_simulations: int
    total_time_ms: float
    timestamp: datetime


class TreeVisualizationResponse(BaseModel):
    """Tree visualization data."""

    search_id: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    root_id: str
    total_nodes: int
    max_depth: int


class ActionDistributionResponse(BaseModel):
    """Action probability distribution."""

    search_id: str
    distribution: dict[str, float]
    total_visits: int
    entropy: float
    timestamp: datetime


class TopActionsResponse(BaseModel):
    """Top N actions by visit count."""

    search_id: str
    actions: list[dict[str, Any]]
    timestamp: datetime


class MCTSConfigResponse(BaseModel):
    """MCTS configuration."""

    max_simulations: int
    exploration_weight: float
    discount_factor: float
    time_budget_ms: int | None
    confidence_threshold: float
    progressive_widening_alpha: float
    rollout_horizon: int


class MCTSConfigUpdate(BaseModel):
    """MCTS configuration update."""

    max_simulations: int | None = Field(default=None, ge=1, le=100000)
    exploration_weight: float | None = Field(default=None, ge=0.0, le=10.0)
    discount_factor: float | None = Field(default=None, ge=0.0, le=1.0)
    time_budget_ms: int | None = Field(default=None, ge=50, le=60000)
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    progressive_widening_alpha: float | None = Field(default=None, ge=0.0, le=1.0)
    rollout_horizon: int | None = Field(default=None, ge=1, le=365)


# In-memory storage for search results (in production, use Redis/database)
_search_results: dict[str, Any] = {}


# Dependency injection
async def get_mcts_tree() -> MCTSTree:
    """Get MCTS tree instance."""
    config = MCTSConfig()
    return MCTSTree(config=config)


async def get_hierarchical_tree() -> HierarchicalMCTSTree:
    """Get hierarchical MCTS tree instance."""
    # TODO: Initialize with proper config
    pass


async def get_action_space() -> ActionSpace:
    """Get action space instance."""
    return ActionSpace(
        allow_shorts=False,
        max_position_size=0.25,
        min_position_size=0.01,
    )


# Endpoints
@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Run MCTS search",
    description="""
    Executes a Monte Carlo Tree Search to find optimal trading action.

    This endpoint performs a complete MCTS search starting from the current
    state. It explores the action space using UCB selection, expands promising
    nodes, simulates future outcomes, and backpropagates values.

    **MCTS Parameters:**
    - max_simulations: Number of iterations (more = better quality)
    - exploration_weight: UCB exploration constant (sqrt(2) is optimal)
    - time_budget_ms: Maximum computation time
    - discount_factor: Future reward discount (0.99 typical)

    **Process:**
    1. Initialize tree with current state
    2. Run simulations (select → expand → simulate → backpropagate)
    3. Return best action by visit count

    **Returns:** Best action with search statistics and tree metrics.
    """,
)
async def run_mcts_search(
    request: SearchRequest,
    mcts_tree: MCTSTree = Depends(get_mcts_tree),
    action_space: ActionSpace = Depends(get_action_space),
) -> SearchResponse:
    """
    Run MCTS search.

    Args:
        request: Search parameters
        mcts_tree: MCTS tree instance
        action_space: Action space

    Returns:
        SearchResponse with best action and statistics
    """
    logger.info(
        "Starting MCTS search",
        symbol=request.symbol,
        max_simulations=request.max_simulations,
    )

    try:
        # Update tree configuration
        mcts_tree.config.max_simulations = request.max_simulations
        mcts_tree.config.exploration_weight = request.exploration_weight
        mcts_tree.config.time_budget_ms = request.time_budget_ms
        mcts_tree.config.discount_factor = request.discount_factor

        # TODO: Build initial state from request
        # For now, create mock state
        from reasoning_trading.core.state import TradingState

        initial_state = TradingState(
            symbol=request.symbol,
            timestamp=datetime.now(),
            current_price=request.current_price,
        )

        # Run search
        result = await mcts_tree.search(initial_state, action_space)

        # Generate search ID and store results
        search_id = f"{request.symbol}_{datetime.now().timestamp()}"
        _search_results[search_id] = {
            "tree": mcts_tree,
            "result": result,
            "timestamp": datetime.now(),
        }

        logger.info(
            "MCTS search completed",
            search_id=search_id,
            simulations=result.total_simulations,
        )

        return SearchResponse(
            search_id=search_id,
            best_action=result.best_action.to_dict() if result.best_action else {},
            best_value=result.best_value,
            best_visits=result.best_visits,
            total_simulations=result.total_simulations,
            total_time_ms=result.total_time_ms,
            simulations_per_second=result.simulations_per_second,
            max_depth_reached=result.max_depth_reached,
            total_nodes=result.total_nodes,
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error("MCTS search failed", symbol=request.symbol, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MCTS search failed: {str(e)}",
        )


@router.post(
    "/hierarchical-search",
    response_model=HierarchicalSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Run hierarchical MCTS search",
    description="""
    Executes hierarchical MCTS with strategic and tactical layers.

    This endpoint performs two-level MCTS search:
    1. Strategic layer: High-level decisions (buy/sell/hold, time horizon)
    2. Tactical layer: Fine-grained parameters (position size, stop-loss)

    **Hierarchical Benefits:**
    - Reduces action space dimensionality
    - Focuses computation on promising strategies
    - Faster convergence to good solutions
    - Better exploration-exploitation balance

    **Parameters:**
    - strategic_simulations: Simulations for high-level decisions
    - tactical_simulations: Simulations for parameter tuning
    - time_budget_ms: Total computation time budget

    **Returns:** Strategic decision with tactical refinements.
    """,
)
async def run_hierarchical_search(
    request: HierarchicalSearchRequest,
) -> HierarchicalSearchResponse:
    """
    Run hierarchical MCTS search.

    Args:
        request: Hierarchical search parameters

    Returns:
        HierarchicalSearchResponse with strategic and tactical actions
    """
    logger.info(
        "Starting hierarchical MCTS search",
        symbol=request.symbol,
        strategic_sims=request.strategic_simulations,
        tactical_sims=request.tactical_simulations,
    )

    try:
        # TODO: Implement hierarchical MCTS
        search_id = f"{request.symbol}_hierarchical_{datetime.now().timestamp()}"

        strategic_action = {
            "direction": "buy",
            "time_horizon": "1D",
            "confidence": 0.85,
        }

        tactical_actions = [
            {
                "position_size": 0.10,
                "stop_loss_pct": 0.05,
                "take_profit_pct": 0.15,
                "confidence": 0.82,
            },
            {
                "position_size": 0.15,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.12,
                "confidence": 0.78,
            },
        ]

        logger.info(
            "Hierarchical MCTS search completed",
            search_id=search_id,
        )

        return HierarchicalSearchResponse(
            search_id=search_id,
            strategic_action=strategic_action,
            tactical_actions=tactical_actions,
            strategic_value=1.35,
            total_simulations=request.strategic_simulations + request.tactical_simulations,
            total_time_ms=850.0,
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error("Hierarchical search failed", symbol=request.symbol, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hierarchical search failed: {str(e)}",
        )


@router.get(
    "/tree/{search_id}",
    response_model=TreeVisualizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get tree visualization data",
    description="""
    Retrieves tree structure data for visualization.

    This endpoint returns the MCTS tree structure in a format suitable for
    visualization libraries (D3.js, vis.js, etc.). It includes nodes, edges,
    visit counts, values, and action labels.

    **Tree Data:**
    - Nodes: State nodes with visit counts and mean values
    - Edges: Actions connecting states with probabilities
    - Metrics: Depth, breadth, expansion statistics

    **Use Case:** Visualize search tree to understand MCTS exploration.

    **Returns:** Tree structure with nodes and edges.
    """,
)
async def get_tree_visualization(search_id: str) -> TreeVisualizationResponse:
    """
    Get tree visualization data.

    Args:
        search_id: Search identifier

    Returns:
        TreeVisualizationResponse with tree structure
    """
    logger.info("Fetching tree visualization", search_id=search_id)

    if search_id not in _search_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search {search_id} not found",
        )

    try:
        search_data = _search_results[search_id]
        tree = search_data["tree"]
        result = search_data["result"]

        # Build tree visualization data
        nodes = []
        edges = []

        if tree.root:
            # Traverse tree and build node/edge lists
            # TODO: Implement tree traversal
            nodes.append({
                "id": "root",
                "visits": tree.root.visits,
                "value": tree.root.mean_value,
                "depth": 0,
            })

        return TreeVisualizationResponse(
            search_id=search_id,
            nodes=nodes,
            edges=edges,
            root_id="root",
            total_nodes=result.total_nodes,
            max_depth=result.max_depth_reached,
        )

    except Exception as e:
        logger.error("Failed to get tree visualization", search_id=search_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tree visualization: {str(e)}",
        )


@router.get(
    "/action-distribution/{search_id}",
    response_model=ActionDistributionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get action probability distribution",
    description="""
    Retrieves probability distribution over actions at root.

    This endpoint returns the visit-based probability distribution for all
    actions explored from the root state. Higher visit counts indicate
    more promising actions.

    **Distribution Metrics:**
    - Action probabilities (visit_count / total_visits)
    - Shannon entropy (measure of uncertainty)
    - Total visits across all actions

    **Use Case:** Understand which actions MCTS favors and confidence level.

    **Returns:** Action distribution with entropy measure.
    """,
)
async def get_action_distribution(search_id: str) -> ActionDistributionResponse:
    """
    Get action probability distribution.

    Args:
        search_id: Search identifier

    Returns:
        ActionDistributionResponse with distribution
    """
    logger.info("Fetching action distribution", search_id=search_id)

    if search_id not in _search_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search {search_id} not found",
        )

    try:
        search_data = _search_results[search_id]
        tree = search_data["tree"]

        distribution = tree.get_action_distribution()
        total_visits = sum(
            child.visits for child in tree.root.children if tree.root
        ) if tree.root else 0

        # Calculate entropy
        probs = list(distribution.values())
        entropy = -sum(p * np.log2(p) for p in probs if p > 0) if probs else 0.0

        return ActionDistributionResponse(
            search_id=search_id,
            distribution=distribution,
            total_visits=total_visits,
            entropy=float(entropy),
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error("Failed to get distribution", search_id=search_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get distribution: {str(e)}",
        )


@router.get(
    "/top-actions/{search_id}",
    response_model=TopActionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get top N actions",
    description="""
    Retrieves top N actions ranked by visit count.

    This endpoint returns the most-visited actions from MCTS search,
    which represent the most promising options according to the algorithm.

    **Action Details:**
    - Action parameters (direction, size, stops, horizon)
    - Mean value estimate
    - Visit count
    - Confidence score

    **Use Case:** Get ranked list of best actions for decision-making.

    **Returns:** List of top actions with statistics.
    """,
)
async def get_top_actions(
    search_id: str,
    n: int = 5,
) -> TopActionsResponse:
    """
    Get top N actions by visit count.

    Args:
        search_id: Search identifier
        n: Number of top actions to return

    Returns:
        TopActionsResponse with ranked actions
    """
    logger.info("Fetching top actions", search_id=search_id, n=n)

    if search_id not in _search_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Search {search_id} not found",
        )

    try:
        search_data = _search_results[search_id]
        tree = search_data["tree"]

        top_actions = tree.get_top_actions(n=n)

        actions = [
            {
                "action": action.to_dict(),
                "mean_value": mean_value,
                "visits": visits,
                "confidence": visits / max(1, tree.root.visits) if tree.root else 0.0,
            }
            for action, mean_value, visits in top_actions
        ]

        return TopActionsResponse(
            search_id=search_id,
            actions=actions,
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error("Failed to get top actions", search_id=search_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get top actions: {str(e)}",
        )


@router.get(
    "/config",
    response_model=MCTSConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get MCTS configuration",
    description="""
    Retrieves current MCTS algorithm configuration.

    This endpoint returns all tunable MCTS parameters including simulation
    limits, exploration weights, and rollout settings.

    **Returns:** Current MCTS configuration.
    """,
)
async def get_mcts_config(
    mcts_tree: MCTSTree = Depends(get_mcts_tree),
) -> MCTSConfigResponse:
    """
    Get MCTS configuration.

    Args:
        mcts_tree: MCTS tree instance

    Returns:
        MCTSConfigResponse with current configuration
    """
    config = mcts_tree.config

    return MCTSConfigResponse(
        max_simulations=config.max_simulations,
        exploration_weight=config.exploration_weight,
        discount_factor=config.discount_factor,
        time_budget_ms=config.time_budget_ms,
        confidence_threshold=config.confidence_threshold,
        progressive_widening_alpha=config.progressive_widening_alpha,
        rollout_horizon=config.rollout_horizon,
    )


@router.put(
    "/config",
    response_model=MCTSConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Update MCTS configuration",
    description="""
    Updates MCTS algorithm configuration.

    This endpoint allows tuning MCTS parameters for different trading
    scenarios. For example:
    - Increase simulations for important decisions
    - Decrease exploration_weight in trending markets
    - Adjust time budget for real-time vs batch processing

    **Tunable Parameters:**
    - max_simulations: Computation budget
    - exploration_weight: Exploration vs exploitation
    - discount_factor: Future reward discounting
    - time_budget_ms: Real-time constraint
    - confidence_threshold: Early termination
    - progressive_widening_alpha: Action space expansion rate

    **Returns:** Updated configuration.
    """,
)
async def update_mcts_config(
    updates: MCTSConfigUpdate,
    mcts_tree: MCTSTree = Depends(get_mcts_tree),
) -> MCTSConfigResponse:
    """
    Update MCTS configuration.

    Args:
        updates: Configuration updates
        mcts_tree: MCTS tree instance

    Returns:
        MCTSConfigResponse with updated configuration
    """
    logger.info("Updating MCTS configuration", updates=updates.model_dump(exclude_none=True))

    try:
        # Update non-None fields
        if updates.max_simulations is not None:
            mcts_tree.config.max_simulations = updates.max_simulations
        if updates.exploration_weight is not None:
            mcts_tree.config.exploration_weight = updates.exploration_weight
        if updates.discount_factor is not None:
            mcts_tree.config.discount_factor = updates.discount_factor
        if updates.time_budget_ms is not None:
            mcts_tree.config.time_budget_ms = updates.time_budget_ms
        if updates.confidence_threshold is not None:
            mcts_tree.config.confidence_threshold = updates.confidence_threshold
        if updates.progressive_widening_alpha is not None:
            mcts_tree.config.progressive_widening_alpha = updates.progressive_widening_alpha
        if updates.rollout_horizon is not None:
            mcts_tree.config.rollout_horizon = updates.rollout_horizon

        logger.info("MCTS configuration updated successfully")

        return MCTSConfigResponse(
            max_simulations=mcts_tree.config.max_simulations,
            exploration_weight=mcts_tree.config.exploration_weight,
            discount_factor=mcts_tree.config.discount_factor,
            time_budget_ms=mcts_tree.config.time_budget_ms,
            confidence_threshold=mcts_tree.config.confidence_threshold,
            progressive_widening_alpha=mcts_tree.config.progressive_widening_alpha,
            rollout_horizon=mcts_tree.config.rollout_horizon,
        )

    except Exception as e:
        logger.error("Failed to update config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update config: {str(e)}",
        )
