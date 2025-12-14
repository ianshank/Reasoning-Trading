"""
Enterprise UI Backend for Reasoning Trading.

FastAPI-based backend providing REST API and WebSocket endpoints for
real-time trading analysis, MCTS-based decision making, and portfolio management.
"""

from importlib.metadata import version

try:
    __version__ = version("reasoning-trading")
except Exception:
    __version__ = "0.1.0"

__all__ = ["__version__"]
