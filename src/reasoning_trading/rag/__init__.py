"""
RAG (Retrieval-Augmented Generation) module for trading intelligence.

This module provides vector database backed retrieval systems for:
- Historical trading patterns and outcomes
- Financial news and research documents
- MCTS strategy trees and decision paths
"""

from __future__ import annotations

from reasoning_trading.rag.base import (
    BaseRAG,
    DocumentChunk,
    RAGConfig,
    RetrievalResult,
)
from reasoning_trading.rag.financial_knowledge import FinancialKnowledgeRAG
from reasoning_trading.rag.mcts_strategies import MCTSStrategyRAG
from reasoning_trading.rag.trading_patterns import TradingPatternRAG

__all__ = [
    "BaseRAG",
    "DocumentChunk",
    "FinancialKnowledgeRAG",
    "MCTSStrategyRAG",
    "RAGConfig",
    "RetrievalResult",
    "TradingPatternRAG",
]
