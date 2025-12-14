"""
Service layer for the FastAPI backend.

This package provides high-level services that integrate with the
reasoning_trading modules:

- TradingService: Trading operations and market analysis
- MCTSService: Tree search with result caching
- PortfolioService: Portfolio management and risk metrics
- AnalyticsService: Performance metrics and Lambda architecture integration
- CacheService: Redis-based caching abstraction

All services use dependency injection, structured logging, and comprehensive
error handling.
"""

from .analytics_service import AnalyticsService
from .cache_service import CacheService
from .exceptions import (
    AnalyticsServiceException,
    CacheServiceException,
    ConfigurationException,
    MCTSServiceException,
    PortfolioServiceException,
    ResourceNotFoundException,
    ServiceException,
    TimeoutException,
    TradingServiceException,
    ValidationException,
)
from .mcts_service import MCTSService
from .portfolio_service import PortfolioService
from .trading_service import TradingService

__all__ = [
    # Services
    "TradingService",
    "MCTSService",
    "PortfolioService",
    "AnalyticsService",
    "CacheService",
    # Exceptions
    "ServiceException",
    "TradingServiceException",
    "MCTSServiceException",
    "PortfolioServiceException",
    "AnalyticsServiceException",
    "CacheServiceException",
    "ValidationException",
    "ResourceNotFoundException",
    "TimeoutException",
    "ConfigurationException",
]
