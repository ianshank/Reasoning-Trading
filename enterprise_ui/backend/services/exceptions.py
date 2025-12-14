"""
Custom exceptions for the service layer.

Provides specific exception types for different error scenarios
with proper error codes and messages.

Implements RFC 7807 compliant error responses.
"""

from typing import Any, Optional

from fastapi import status


class ServiceException(Exception):
    """Base exception for all service layer errors with RFC 7807 support."""

    def __init__(
        self,
        message: str,
        error_code: str = "service_error",
        details: Optional[dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type_uri: str = "about:blank",
        instance: Optional[str] = None,
    ):
        """
        Initialize service exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            status_code: HTTP status code
            error_type_uri: URI reference for the error type
            instance: URI reference identifying the specific occurrence
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        self.error_type_uri = error_type_uri
        self.instance = instance

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to RFC 7807 Problem Details dictionary for API responses.

        Returns:
            Dictionary with RFC 7807 compliant error format
        """
        problem = {
            "type": self.error_type_uri,
            "title": self.error_code.replace("_", " ").title(),
            "status": self.status_code,
            "detail": self.message,
        }

        # Add instance if provided
        if self.instance:
            problem["instance"] = self.instance

        # Add additional details if present
        if self.details:
            problem.update(self.details)

        return problem


class TradingServiceException(ServiceException):
    """Exception raised by TradingService."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        instance: Optional[str] = None,
    ):
        super().__init__(
            message,
            error_code="trading_error",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            instance=instance,
        )


class MCTSServiceException(ServiceException):
    """Exception raised by MCTSService."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        instance: Optional[str] = None,
    ):
        super().__init__(
            message,
            error_code="mcts_error",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            instance=instance,
        )


class PortfolioServiceException(ServiceException):
    """Exception raised by PortfolioService."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        instance: Optional[str] = None,
    ):
        super().__init__(
            message,
            error_code="portfolio_error",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            instance=instance,
        )


class AnalyticsServiceException(ServiceException):
    """Exception raised by AnalyticsService."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        instance: Optional[str] = None,
    ):
        super().__init__(
            message,
            error_code="analytics_error",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            instance=instance,
        )


class CacheServiceException(ServiceException):
    """Exception raised by CacheService."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        instance: Optional[str] = None,
    ):
        super().__init__(
            message,
            error_code="cache_error",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            instance=instance,
        )


class ValidationException(ServiceException):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        instance: Optional[str] = None,
    ):
        details = {"field": field} if field else {}
        super().__init__(
            message,
            error_code="validation_error",
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            instance=instance,
        )


class ResourceNotFoundException(ServiceException):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        instance: Optional[str] = None,
    ):
        message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(
            message,
            error_code="resource_not_found",
            details={"resource_type": resource_type, "resource_id": resource_id},
            status_code=status.HTTP_404_NOT_FOUND,
            instance=instance,
        )


class TimeoutException(ServiceException):
    """Exception raised when an operation times out."""

    def __init__(
        self,
        operation: str,
        timeout_ms: int,
        instance: Optional[str] = None,
    ):
        message = f"Operation '{operation}' timed out after {timeout_ms}ms"
        super().__init__(
            message,
            error_code="timeout",
            details={"operation": operation, "timeout_ms": timeout_ms},
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            instance=instance,
        )


class ConfigurationException(ServiceException):
    """Exception raised for configuration errors."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        instance: Optional[str] = None,
    ):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(
            message,
            error_code="configuration_error",
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            instance=instance,
        )
