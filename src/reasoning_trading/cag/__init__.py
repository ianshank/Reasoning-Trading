"""
CAG (Cache-Augmented Generation) module for trading decisions.

This module provides semantic caching systems for:
- Trading decisions with similarity matching
- LLM analyst responses
- Hierarchical multi-level caching (L1 → L2 → L3)
"""

from __future__ import annotations

from reasoning_trading.cag.base import (
    BaseCAG,
    CacheEntry,
    CacheHit,
    CAGConfig,
)
from reasoning_trading.cag.analyst_cache import AnalystResponseCAG
from reasoning_trading.cag.hierarchical_cache import HierarchicalCAG
from reasoning_trading.cag.semantic_cache import SemanticDecisionCache

__all__ = [
    "AnalystResponseCAG",
    "BaseCAG",
    "CacheEntry",
    "CacheHit",
    "CAGConfig",
    "HierarchicalCAG",
    "SemanticDecisionCache",
]
