"""
Custom exceptions for the service layer.

Provides specific exception types for different error scenarios
with proper error codes and messages.
"""

from typing import Any, Optional


class ServiceException(Exception):
    """Base exception for all service layer errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "SERVICE_ERROR",
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize service exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class TradingServiceException(ServiceException):
    """Exception raised by TradingService."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "TRADING_ERROR", details)


class MCTSServiceException(ServiceException):
    """Exception raised by MCTSService."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "MCTS_ERROR", details)


class PortfolioServiceException(ServiceException):
    """Exception raised by PortfolioService."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "PORTFOLIO_ERROR", details)


class AnalyticsServiceException(ServiceException):
    """Exception raised by AnalyticsService."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "ANALYTICS_ERROR", details)


class CacheServiceException(ServiceException):
    """Exception raised by CacheService."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message, "CACHE_ERROR", details)


class ValidationException(ServiceException):
    """Exception raised for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, "VALIDATION_ERROR", details)


class ResourceNotFoundException(ServiceException):
    """Exception raised when a requested resource is not found."""

    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(
            message,
            "RESOURCE_NOT_FOUND",
            {"resource_type": resource_type, "resource_id": resource_id},
        )


class TimeoutException(ServiceException):
    """Exception raised when an operation times out."""

    def __init__(self, operation: str, timeout_ms: int):
        message = f"Operation '{operation}' timed out after {timeout_ms}ms"
        super().__init__(
            message,
            "TIMEOUT",
            {"operation": operation, "timeout_ms": timeout_ms},
        )


class ConfigurationException(ServiceException):
    """Exception raised for configuration errors."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, "CONFIGURATION_ERROR", details)
