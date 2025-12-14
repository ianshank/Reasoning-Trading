"""
Debugging utilities for the enterprise UI backend.

This module provides comprehensive debugging tools including:
- Debug context manager
- Performance profiling decorator
- Memory usage tracking
- Request/response dumping for development
"""

import cProfile
import functools
import io
import json
import os
import pstats
import sys
import time
import tracemalloc
from contextlib import contextmanager
from typing import Any, Callable, Optional, TypeVar, cast
from pstats import SortKey

from .logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def is_debug_mode() -> bool:
    """
    Check if debug mode is enabled.

    Returns:
        True if debug mode is enabled
    """
    return os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")


def is_development() -> bool:
    """
    Check if running in development environment.

    Returns:
        True if in development environment
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    return env == "development"


class DebugContext:
    """
    Context manager for debugging with automatic timing and logging.

    Example:
        with DebugContext("database_query", query="SELECT * FROM users"):
            result = execute_query()
    """

    def __init__(self, operation: str, **context: Any):
        """
        Initialize debug context.

        Args:
            operation: Name of the operation being debugged
            **context: Additional context information
        """
        self.operation = operation
        self.context = context
        self.start_time: Optional[float] = None
        self.enabled = is_debug_mode()

    def __enter__(self) -> "DebugContext":
        """Enter the debug context."""
        if self.enabled:
            self.start_time = time.time()
            logger.debug(
                "debug_context_enter",
                operation=self.operation,
                **self.context,
            )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the debug context and log timing."""
        if self.enabled and self.start_time:
            duration = time.time() - self.start_time
            if exc_type:
                logger.debug(
                    "debug_context_error",
                    operation=self.operation,
                    duration_ms=round(duration * 1000, 2),
                    error_type=exc_type.__name__,
                    error_message=str(exc_val),
                    **self.context,
                )
            else:
                logger.debug(
                    "debug_context_exit",
                    operation=self.operation,
                    duration_ms=round(duration * 1000, 2),
                    **self.context,
                )


def profile_function(
    sort_by: SortKey = SortKey.CUMULATIVE,
    top_n: int = 20,
    print_stats: bool = True,
) -> Callable[[F], F]:
    """
    Decorator to profile function execution using cProfile.

    Example:
        @profile_function(sort_by=SortKey.TIME, top_n=10)
        def expensive_function():
            # ... complex logic ...
            pass

    Args:
        sort_by: How to sort the profiling results
        top_n: Number of top results to show
        print_stats: Whether to print stats to stdout

    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not is_debug_mode():
                return func(*args, **kwargs)

            profiler = cProfile.Profile()
            profiler.enable()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                profiler.disable()

                # Capture stats
                stream = io.StringIO()
                stats = pstats.Stats(profiler, stream=stream)
                stats.sort_stats(sort_by)
                stats.print_stats(top_n)

                # Log the profiling results
                profile_output = stream.getvalue()
                logger.info(
                    "function_profiled",
                    function=func.__name__,
                    profile_data=profile_output,
                )

                if print_stats:
                    logger.debug(
                        "profile_stats_output",
                        function=func.__name__,
                        output=profile_output,
                    )

        return cast(F, wrapper)

    return decorator


class MemoryTracker:
    """
    Context manager for tracking memory usage.

    Example:
        with MemoryTracker("data_processing") as tracker:
            large_data = process_large_dataset()
        print(f"Peak memory: {tracker.peak_memory_mb}MB")
    """

    def __init__(self, operation: str, log_results: bool = True):
        """
        Initialize memory tracker.

        Args:
            operation: Name of the operation being tracked
            log_results: Whether to log results automatically
        """
        self.operation = operation
        self.log_results = log_results
        self.snapshot_start: Optional[Any] = None
        self.snapshot_end: Optional[Any] = None
        self.enabled = is_debug_mode()
        self.peak_memory: int = 0

    def __enter__(self) -> "MemoryTracker":
        """Start memory tracking."""
        if self.enabled:
            if not tracemalloc.is_tracing():
                tracemalloc.start()
            self.snapshot_start = tracemalloc.take_snapshot()
            tracemalloc.reset_peak()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop memory tracking and log results."""
        if self.enabled and self.snapshot_start:
            self.snapshot_end = tracemalloc.take_snapshot()
            current, peak = tracemalloc.get_traced_memory()
            self.peak_memory = peak

            if self.log_results:
                top_stats = self.snapshot_end.compare_to(
                    self.snapshot_start, 'lineno'
                )

                logger.info(
                    "memory_usage",
                    operation=self.operation,
                    current_memory_mb=round(current / 1024 / 1024, 2),
                    peak_memory_mb=round(peak / 1024 / 1024, 2),
                    top_allocations=[
                        {
                            "file": stat.traceback.format()[0],
                            "size_mb": round(stat.size / 1024 / 1024, 4),
                            "count": stat.count,
                        }
                        for stat in top_stats[:10]
                    ],
                )

    @property
    def peak_memory_mb(self) -> float:
        """Get peak memory usage in megabytes."""
        return round(self.peak_memory / 1024 / 1024, 2)


@contextmanager
def dump_request_response(
    request_data: Optional[dict[str, Any]] = None,
    operation: str = "api_call",
):
    """
    Context manager to dump request and response data for debugging.

    Example:
        with dump_request_response(
            request_data={"user_id": 123},
            operation="create_order"
        ) as dumper:
            response = create_order(user_id=123)
            dumper.set_response(response)

    Args:
        request_data: Request data to log
        operation: Name of the operation

    Yields:
        ResponseDumper instance
    """
    dumper = ResponseDumper(operation, request_data)

    if is_development():
        logger.debug(
            "request_dump",
            operation=operation,
            request=_safe_serialize(request_data),
        )

    try:
        yield dumper
    finally:
        if is_development() and dumper.response_data is not None:
            logger.debug(
                "response_dump",
                operation=operation,
                response=_safe_serialize(dumper.response_data),
            )


class ResponseDumper:
    """Helper class for response dumping."""

    def __init__(self, operation: str, request_data: Optional[dict[str, Any]] = None):
        """
        Initialize response dumper.

        Args:
            operation: Operation name
            request_data: Request data
        """
        self.operation = operation
        self.request_data = request_data
        self.response_data: Optional[Any] = None

    def set_response(self, response: Any) -> None:
        """
        Set the response data to be dumped.

        Args:
            response: Response data
        """
        self.response_data = response


def _safe_serialize(obj: Any) -> Any:
    """
    Safely serialize an object for logging.

    Args:
        obj: Object to serialize

    Returns:
        Serializable representation of the object
    """
    if obj is None:
        return None

    # Try JSON serialization first
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        pass

    # Handle common types
    if isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_safe_serialize(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        return _safe_serialize(obj.__dict__)
    else:
        return str(obj)


def trace_calls(func: F) -> F:
    """
    Decorator to trace function calls with detailed logging.

    Only active in debug mode.

    Example:
        @trace_calls
        def complex_calculation(x, y):
            return x * y + x / y

    Args:
        func: Function to trace

    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not is_debug_mode():
            return func(*args, **kwargs)

        # Log function entry
        logger.debug(
            "trace_function_call",
            function=func.__name__,
            module=func.__module__,
            args=_safe_serialize(args),
            kwargs=_safe_serialize(kwargs),
        )

        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            # Log successful return
            logger.debug(
                "trace_function_return",
                function=func.__name__,
                duration_ms=round(duration * 1000, 2),
                result=_safe_serialize(result),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time

            # Log exception
            logger.debug(
                "trace_function_exception",
                function=func.__name__,
                duration_ms=round(duration * 1000, 2),
                exception_type=type(e).__name__,
                exception_message=str(e),
                traceback=traceback.format_exc(),
            )

            raise

    return cast(F, wrapper)


def print_debug_info() -> None:
    """Print general debug information about the environment."""
    if not is_debug_mode():
        return

    info = {
        "python_version": sys.version,
        "platform": sys.platform,
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "debug_mode": is_debug_mode(),
        "pid": os.getpid(),
    }

    logger.debug("debug_info", **info)
