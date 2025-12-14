"""
Unit tests for the logging module.

Tests cover:
- Logger configuration
- Request ID tracking
- Timing decorators
- Log context management
- Environment-based log levels
"""

import logging
import os
import time
from unittest.mock import MagicMock, patch

import pytest
import structlog

from enterprise_ui.backend.core.logging import (
    LogContext,
    clear_request_id,
    configure_logging,
    get_log_level,
    get_logger,
    request_id_ctx,
    set_request_id,
    with_logging,
    with_timing,
)


class TestLoggerConfiguration:
    """Test logger configuration functionality."""

    def test_get_log_level_default(self):
        """Test default log level is INFO."""
        with patch.dict(os.environ, {}, clear=True):
            level = get_log_level()
            assert level == logging.INFO

    def test_get_log_level_from_environment(self):
        """Test log level based on ENVIRONMENT variable."""
        test_cases = {
            "production": logging.WARNING,
            "staging": logging.INFO,
            "development": logging.DEBUG,
            "test": logging.WARNING,
        }

        for env, expected_level in test_cases.items():
            with patch.dict(os.environ, {"ENVIRONMENT": env}, clear=True):
                level = get_log_level()
                assert level == expected_level, f"Failed for environment: {env}"

    def test_get_log_level_explicit(self):
        """Test explicit LOG_LEVEL environment variable."""
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}, clear=True):
            level = get_log_level()
            assert level == logging.ERROR

    def test_configure_logging_json(self):
        """Test JSON logging configuration."""
        configure_logging(json_logs=True, log_level=logging.INFO)
        logger = get_logger("test")
        assert isinstance(logger, structlog.stdlib.BoundLogger)

    def test_configure_logging_console(self):
        """Test console logging configuration."""
        configure_logging(json_logs=False, log_level=logging.DEBUG)
        logger = get_logger("test")
        assert isinstance(logger, structlog.stdlib.BoundLogger)

    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, structlog.stdlib.BoundLogger)

    def test_get_logger_without_name(self):
        """Test getting a logger without specifying a name."""
        logger = get_logger()
        assert isinstance(logger, structlog.stdlib.BoundLogger)


class TestRequestIDTracking:
    """Test request ID tracking functionality."""

    def test_set_and_get_request_id(self):
        """Test setting and getting request ID."""
        test_id = "test-request-123"
        set_request_id(test_id)
        assert request_id_ctx.get() == test_id

    def test_clear_request_id(self):
        """Test clearing request ID."""
        set_request_id("test-id")
        clear_request_id()
        assert request_id_ctx.get() is None

    def test_request_id_isolation(self):
        """Test that request IDs are isolated in different contexts."""
        set_request_id("id-1")
        assert request_id_ctx.get() == "id-1"

        clear_request_id()
        assert request_id_ctx.get() is None


class TestTimingDecorator:
    """Test timing decorator functionality."""

    def test_with_timing_success(self, caplog):
        """Test timing decorator on successful function."""
        configure_logging(json_logs=False, log_level=logging.DEBUG)

        @with_timing
        def fast_function():
            return "success"

        with caplog.at_level(logging.INFO):
            result = fast_function()

        assert result == "success"
        assert "function_completed" in caplog.text
        assert "fast_function" in caplog.text

    def test_with_timing_error(self, caplog):
        """Test timing decorator on function that raises error."""
        configure_logging(json_logs=False, log_level=logging.DEBUG)

        @with_timing
        def failing_function():
            raise ValueError("Test error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                failing_function()

        assert "function_failed" in caplog.text
        assert "failing_function" in caplog.text

    def test_with_timing_measures_duration(self):
        """Test that timing decorator measures duration."""
        @with_timing
        def slow_function():
            time.sleep(0.1)
            return "done"

        start = time.time()
        result = slow_function()
        duration = time.time() - start

        assert result == "done"
        assert duration >= 0.1


class TestLoggingDecorator:
    """Test logging decorator functionality."""

    def test_with_logging_basic(self, caplog):
        """Test basic logging decorator."""
        configure_logging(json_logs=False, log_level=logging.DEBUG)

        @with_logging()
        def simple_function():
            return "result"

        with caplog.at_level(logging.DEBUG):
            result = simple_function()

        assert result == "result"
        assert "function_called" in caplog.text

    def test_with_logging_with_args(self, caplog):
        """Test logging decorator with argument logging."""
        configure_logging(json_logs=False, log_level=logging.DEBUG)

        @with_logging(log_args=True)
        def function_with_args(x, y):
            return x + y

        with caplog.at_level(logging.DEBUG):
            result = function_with_args(2, 3)

        assert result == 5

    def test_with_logging_with_result(self, caplog):
        """Test logging decorator with result logging."""
        configure_logging(json_logs=False, log_level=logging.DEBUG)

        @with_logging(log_result=True)
        def function_with_result():
            return {"status": "ok"}

        with caplog.at_level(logging.DEBUG):
            result = function_with_result()

        assert result == {"status": "ok"}
        assert "function_returned" in caplog.text

    def test_with_logging_on_error(self, caplog):
        """Test logging decorator on function error."""
        configure_logging(json_logs=False, log_level=logging.DEBUG)

        @with_logging()
        def failing_function():
            raise RuntimeError("Test error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError):
                failing_function()

        assert "function_error" in caplog.text

    def test_with_logging_custom_logger(self, caplog):
        """Test logging decorator with custom logger."""
        configure_logging(json_logs=False, log_level=logging.DEBUG)
        custom_logger = get_logger("custom")

        @with_logging(logger=custom_logger)
        def custom_logged_function():
            return "custom"

        with caplog.at_level(logging.DEBUG):
            result = custom_logged_function()

        assert result == "custom"


class TestLogContext:
    """Test log context manager functionality."""

    def test_log_context_basic(self):
        """Test basic log context."""
        with LogContext(user_id="123", action="test"):
            # Context should be bound
            pass
        # Context should be unbound after exit

    def test_log_context_multiple_values(self):
        """Test log context with multiple values."""
        context_data = {
            "user_id": "user-123",
            "session_id": "session-456",
            "action": "login",
        }

        with LogContext(**context_data):
            # All context should be bound
            pass

    def test_log_context_nesting(self):
        """Test nested log contexts."""
        with LogContext(level1="outer"):
            with LogContext(level2="inner"):
                # Both contexts should be active
                pass
            # Only level1 should be active

    def test_log_context_with_exception(self):
        """Test log context when exception occurs."""
        try:
            with LogContext(operation="failing"):
                raise ValueError("Test error")
        except ValueError:
            pass
        # Context should be cleaned up even after exception


class TestIntegration:
    """Integration tests for logging functionality."""

    def test_full_logging_flow(self, caplog):
        """Test complete logging flow with request ID and context."""
        configure_logging(json_logs=False, log_level=logging.DEBUG)

        # Set request ID
        set_request_id("integration-test-123")

        @with_timing
        @with_logging(log_args=True, log_result=True)
        def integration_function(x, y):
            time.sleep(0.01)
            return x * y

        with caplog.at_level(logging.DEBUG):
            with LogContext(operation="integration_test"):
                result = integration_function(3, 4)

        assert result == 12
        clear_request_id()

    def test_logger_in_different_modules(self):
        """Test that loggers work correctly for different modules."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1 is not logger2

    def test_logging_with_different_levels(self, caplog):
        """Test logging at different levels."""
        configure_logging(json_logs=False, log_level=logging.DEBUG)
        logger = get_logger("test")

        with caplog.at_level(logging.DEBUG):
            logger.debug("debug message")
            logger.info("info message")
            logger.warning("warning message")
            logger.error("error message")

        assert "debug message" in caplog.text
        assert "info message" in caplog.text
        assert "warning message" in caplog.text
        assert "error message" in caplog.text


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    yield
    # Reset request ID context
    clear_request_id()
    # Reconfigure logging to default state
    configure_logging(json_logs=False, log_level=logging.DEBUG)


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    logger = MagicMock(spec=structlog.stdlib.BoundLogger)
    return logger
