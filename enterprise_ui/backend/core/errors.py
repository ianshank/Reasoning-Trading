"""
Error handling utilities for secure exception masking.

This module provides utilities to prevent information disclosure through
error messages by masking internal errors in production while preserving
detailed logging for debugging.

Implements RFC 7807 (Problem Details for HTTP APIs) for standardized error responses.
"""

from enum import Enum
from typing import Any, Optional

import structlog
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from enterprise_ui.backend.config import get_backend_settings


class ErrorCode(str, Enum):
    """Machine-readable error codes for API errors."""

    # General errors
    INTERNAL_SERVER_ERROR = "internal_server_error"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT = "timeout"

    # Service-specific errors
    TRADING_ERROR = "trading_error"
    MCTS_ERROR = "mcts_error"
    PORTFOLIO_ERROR = "portfolio_error"
    ANALYTICS_ERROR = "analytics_error"
    CACHE_ERROR = "cache_error"
    CONFIGURATION_ERROR = "configuration_error"
    RESOURCE_NOT_FOUND = "resource_not_found"


class ProblemDetail(BaseModel):
    """
    RFC 7807 Problem Details model for HTTP API errors.

    This model represents a standardized error response format that provides
    machine-readable error information while maintaining human readability.

    Attributes:
        type: URI reference identifying the problem type (defaults to about:blank)
        title: Short, human-readable summary of the problem type
        status: HTTP status code for this occurrence
        detail: Human-readable explanation specific to this occurrence
        instance: URI reference identifying the specific occurrence of the problem
    """

    type: str = Field(
        default="about:blank",
        description="URI reference that identifies the problem type",
    )
    title: str = Field(
        description="Short, human-readable summary of the problem type"
    )
    status: int = Field(
        description="HTTP status code for this occurrence"
    )
    detail: str = Field(
        description="Human-readable explanation specific to this occurrence"
    )
    instance: Optional[str] = Field(
        default=None,
        description="URI reference identifying the specific occurrence",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "type": "https://api.example.com/errors/trading-error",
                "title": "Trading Operation Failed",
                "status": 500,
                "detail": "Failed to execute trade order due to market conditions",
                "instance": "/api/v1/trading/orders/123",
            }
        }


def handle_error(
    logger: Any,
    error: Exception,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    generic_message: str = "An error occurred",
    log_message: str | None = None,
    error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
    error_type_uri: str | None = None,
    instance: str | None = None,
    **log_context: Any,
) -> dict[str, Any]:
    """
    Handle errors securely by logging full details and returning RFC 7807 compliant responses.

    This function ensures that internal error details are not exposed to clients in
    production while maintaining comprehensive error logging for debugging.

    Behavior:
    - In production: Returns generic error message to client
    - In development/test: Returns full error message to client
    - Always logs full error details with exc_info=True
    - Returns RFC 7807 Problem Details format

    Args:
        logger: Structlog logger instance
        error: The exception that occurred
        status_code: HTTP status code to return (default: 500)
        generic_message: Generic message to show in production (default: "An error occurred")
        log_message: Message for logging (if None, uses generic_message)
        error_code: Machine-readable error code from ErrorCode enum
        error_type_uri: URI reference for the error type (defaults to about:blank)
        instance: URI reference identifying the specific occurrence
        **log_context: Additional context to include in log

    Returns:
        RFC 7807 Problem Details dictionary

    Example:
        ```python
        try:
            risky_operation()
        except Exception as e:
            problem = handle_error(
                logger=logger,
                error=e,
                generic_message="Failed to process request",
                log_message="Operation failed",
                error_code=ErrorCode.TRADING_ERROR,
                instance="/api/v1/trading/orders/123",
                symbol="AAPL",
                user_id=123,
            )
            return JSONResponse(
                status_code=problem["status"],
                content=problem,
                media_type="application/problem+json"
            )
        ```
    """
    settings = get_backend_settings()

    # Log the full error with context
    log_msg = log_message or generic_message
    logger.error(
        log_msg,
        error=str(error),
        error_type=type(error).__name__,
        error_code=error_code.value,
        exc_info=True,
        **log_context,
    )

    # In production, return generic message
    # In development/test, return detailed error for debugging
    if settings.is_production:
        detail = generic_message
    else:
        # Include error details in development for easier debugging
        detail = f"{generic_message}: {str(error)}"

    # Create RFC 7807 Problem Details response
    problem = ProblemDetail(
        type=error_type_uri or "about:blank",
        title=error_code.value.replace("_", " ").title(),
        status=status_code,
        detail=detail,
        instance=instance,
    )

    return problem.model_dump(exclude_none=True)
