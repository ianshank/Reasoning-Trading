"""
Hierarchical MCTS implementation with MAXQ decomposition.

This module provides a hierarchical task decomposition for trading that reduces
computational complexity from O(|A|^T) to O(|Ã|^(T/L)) by organizing decisions
into Strategic, Tactical, and Execution levels.
"""

from reasoning_trading.hierarchical.levels import (
    HierarchyLevel,
    StrategicLevel,
    TacticalLevel,
    ExecutionLevel,
)
from reasoning_trading.hierarchical.node import HierarchicalNode
from reasoning_trading.hierarchical.tree import HierarchicalMCTSTree, HierarchicalMCTSConfig
from reasoning_trading.hierarchical.maxq import (
    MAXQValueDecomposition,
    CompletionFunction,
    SubtaskValue,
)
from reasoning_trading.hierarchical.state import HierarchicalState, StateAbstraction

__all__ = [
    "HierarchyLevel",
    "StrategicLevel",
    "TacticalLevel",
    "ExecutionLevel",
    "HierarchicalNode",
    "HierarchicalMCTSTree",
    "HierarchicalMCTSConfig",
    "MAXQValueDecomposition",
    "CompletionFunction",
    "SubtaskValue",
    "HierarchicalState",
    "StateAbstraction",
]
