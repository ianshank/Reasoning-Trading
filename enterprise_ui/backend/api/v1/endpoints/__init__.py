"""
API v1 endpoints package.

This package contains all REST API endpoints organized by domain:
- trading: Trading analysis and execution
- mcts: MCTS search operations
- portfolio: Portfolio management
- regime: Market regime detection
- analytics: Performance analytics
- system: System health and configuration
"""

from enterprise_ui.backend.api.v1.endpoints import (
    analytics,
    mcts,
    portfolio,
    regime,
    system,
    trading,
)

__all__ = [
    "trading",
    "mcts",
    "portfolio",
    "regime",
    "analytics",
    "system",
]
