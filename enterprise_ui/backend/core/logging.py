"""
Structured logging setup using structlog for the enterprise UI backend.

This module provides a comprehensive logging configuration with:
- JSON and console formatters
- Request ID tracking
- Timing decorators
- Environment-based log levels
- Integration with standard Python logging
"""

import logging
import os
import sys
import time
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

import structlog
from structlog.types import EventDict, Processor

# Context variable for request ID tracking
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Type variable for decorators
F = TypeVar("F", bound=Callable[..., Any])


def add_request_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add request ID to log entries if available.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary

    Returns:
        Updated event dictionary with request_id
    """
    request_id = request_id_ctx.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add ISO timestamp to log entries.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary

    Returns:
        Updated event dictionary with timestamp
    """
    event_dict["timestamp"] = time.time()
    return event_dict


def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add log level to event dict.

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary

    Returns:
        Updated event dictionary with level
    """
    if method_name == "warn":
        # Normalize "warn" to "warning"
        event_dict["level"] = "warning"
    else:
        event_dict["level"] = method_name
    return event_dict


def get_log_level() -> int:
    """
    Get log level based on environment.

    Returns:
        Log level constant from logging module
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    log_level_str = os.getenv("LOG_LEVEL", "").upper()

    # If LOG_LEVEL is explicitly set, use it
    if log_level_str:
        return getattr(logging, log_level_str, logging.INFO)

    # Otherwise, use environment-based defaults
    level_mapping = {
        "production": logging.WARNING,
        "staging": logging.INFO,
        "development": logging.DEBUG,
        "test": logging.WARNING,
    }
    return level_mapping.get(env, logging.INFO)


def configure_logging(
    json_logs: Optional[bool] = None,
    log_level: Optional[int] = None,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        json_logs: Whether to use JSON format (default: True in production)
        log_level: Log level to use (default: environment-based)
    """
    # Determine if we should use JSON logs
    if json_logs is None:
        env = os.getenv("ENVIRONMENT", "development").lower()
        json_logs = env == "production"

    # Determine log level
    if log_level is None:
        log_level = get_log_level()

    # Shared processors for both configurations
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_request_id,
        add_log_level,
        add_timestamp,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # JSON logging for production
        processors: list[Processor] = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console logging for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (default: caller's module name)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def set_request_id(request_id: str) -> None:
    """
    Set the request ID for the current context.

    Args:
        request_id: The request ID to set
    """
    request_id_ctx.set(request_id)


def clear_request_id() -> None:
    """Clear the request ID from the current context."""
    request_id_ctx.set(None)


def with_timing(func: F) -> F:
    """
    Decorator to log function execution time.

    Example:
        @with_timing
        def slow_function():
            time.sleep(1)
            return "done"

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    logger = get_logger(func.__module__)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(
                "function_completed",
                function=func.__name__,
                duration_ms=round(duration * 1000, 2),
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "function_failed",
                function=func.__name__,
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                exc_info=True,
            )
            raise

    return cast(F, wrapper)


def with_logging(
    logger: Optional[structlog.stdlib.BoundLogger] = None,
    log_args: bool = False,
    log_result: bool = False,
) -> Callable[[F], F]:
    """
    Decorator to log function calls with optional args and result logging.

    Example:
        @with_logging(log_args=True, log_result=True)
        def add(a, b):
            return a + b

    Args:
        logger: Logger to use (default: creates one from function's module)
        log_args: Whether to log function arguments
        log_result: Whether to log function result

    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            log_data = {"function": func.__name__}

            if log_args:
                log_data["args"] = args
                log_data["kwargs"] = kwargs

            logger.debug("function_called", **log_data)

            try:
                result = func(*args, **kwargs)

                if log_result:
                    logger.debug(
                        "function_returned",
                        function=func.__name__,
                        result=result,
                    )

                return result
            except Exception as e:
                logger.error(
                    "function_error",
                    function=func.__name__,
                    error=str(e),
                    exc_info=True,
                )
                raise

        return cast(F, wrapper)

    return decorator


class LogContext:
    """
    Context manager for adding structured context to logs.

    Example:
        with LogContext(user_id="123", action="login"):
            logger.info("User logged in")
            # Logs will include user_id and action
    """

    def __init__(self, **kwargs: Any):
        """
        Initialize log context.

        Args:
            **kwargs: Context key-value pairs
        """
        self.context = kwargs
        self.tokens: list[object] = []

    def __enter__(self) -> "LogContext":
        """Enter the context and bind context variables."""
        for key, value in self.context.items():
            token = structlog.contextvars.bind_contextvars(**{key: value})
            self.tokens.append(token)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context and unbind context variables."""
        structlog.contextvars.unbind_contextvars(*list(self.context.keys()))


# Initialize logging on module import
configure_logging()
