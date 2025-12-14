"""
Error handling utilities for secure exception masking.

This module provides utilities to prevent information disclosure through
error messages by masking internal errors in production while preserving
detailed logging for debugging.
"""

from typing import Any

import structlog
from fastapi import HTTPException, status

from enterprise_ui.backend.config import get_backend_settings


def handle_error(
    logger: Any,
    error: Exception,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    generic_message: str = "An error occurred",
    log_message: str | None = None,
    **log_context: Any,
) -> HTTPException:
    """
    Handle errors securely by logging full details and returning safe messages to clients.

    This function ensures that internal error details are not exposed to clients in
    production while maintaining comprehensive error logging for debugging.

    Behavior:
    - In production: Returns generic error message to client
    - In development/test: Returns full error message to client
    - Always logs full error details with exc_info=True

    Args:
        logger: Structlog logger instance
        error: The exception that occurred
        status_code: HTTP status code to return (default: 500)
        generic_message: Generic message to show in production (default: "An error occurred")
        log_message: Message for logging (if None, uses generic_message)
        **log_context: Additional context to include in log

    Returns:
        HTTPException with appropriate message based on environment

    Example:
        ```python
        try:
            risky_operation()
        except Exception as e:
            raise handle_error(
                logger=logger,
                error=e,
                generic_message="Failed to process request",
                log_message="Operation failed",
                symbol="AAPL",
                user_id=123,
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

    return HTTPException(
        status_code=status_code,
        detail=detail,
    )
