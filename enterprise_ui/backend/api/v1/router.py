"""
Main API v1 router aggregating all endpoints.

This module combines all API endpoint routers into a single v1 router:
- Trading: Trading analysis and execution
- MCTS: MCTS search operations
- Portfolio: Portfolio management
- Regime: Market regime detection
- Analytics: Performance analytics
- System: System health and configuration
"""

from __future__ import annotations

from fastapi import APIRouter

from enterprise_ui.backend.api.v1.endpoints import (
    analytics,
    mcts,
    portfolio,
    regime,
    system,
    trading,
)
from enterprise_ui.backend.core.logging import get_logger

logger = get_logger(__name__)

# Create main v1 API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(trading.router)
api_router.include_router(mcts.router)
api_router.include_router(portfolio.router)
api_router.include_router(regime.router)
api_router.include_router(analytics.router)
api_router.include_router(system.router)

logger.info(
    "api_v1_router_initialized",
    routers=[
        "trading",
        "mcts",
        "portfolio",
        "regime",
        "analytics",
        "system",
    ],
)
