# =============================================================================
# Reasoning Trading - Multi-stage Dockerfile
# =============================================================================
# Build stages:
#   1. base        - Common base image with Python
#   2. builder     - Build dependencies and wheels
#   3. development - Full development environment
#   4. production  - Minimal production image
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base Image
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 trading \
    && useradd --uid 1000 --gid trading --shell /bin/bash --create-home trading

# Set working directory
WORKDIR /app

# -----------------------------------------------------------------------------
# Stage 2: Builder
# -----------------------------------------------------------------------------
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Copy only dependency files first (for better caching)
COPY pyproject.toml ./

# Install dependencies (without the package itself)
RUN pip install --no-deps -e . 2>/dev/null || true
RUN pip install \
    langchain>=0.3.0 \
    langchain-openai>=0.2.0 \
    langchain-anthropic>=0.2.0 \
    langchain-experimental>=0.3.0 \
    langgraph>=0.2.0 \
    alpaca-py>=0.30.0 \
    finnhub-python>=2.4.0 \
    yfinance>=0.2.40 \
    numpy>=1.24.0 \
    pandas>=2.0.0 \
    scipy>=1.11.0 \
    httpx>=0.27.0 \
    aiohttp>=3.9.0 \
    fastapi>=0.115.0 \
    uvicorn>=0.32.0 \
    redis>=5.0.0 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    python-dotenv>=1.0.0 \
    structlog>=24.1.0 \
    tenacity>=8.2.0 \
    rich>=13.7.0

# Copy source code
COPY src/ ./src/

# Install the package
RUN pip install -e .

# -----------------------------------------------------------------------------
# Stage 3: Development
# -----------------------------------------------------------------------------
FROM builder AS development

# Install development dependencies
RUN pip install \
    pytest>=8.0.0 \
    pytest-asyncio>=0.23.0 \
    pytest-cov>=4.1.0 \
    pytest-mock>=3.12.0 \
    hypothesis>=6.100.0 \
    mypy>=1.8.0 \
    ruff>=0.4.0 \
    pre-commit>=3.6.0 \
    ipython

# Install analysis dependencies
RUN pip install \
    stockstats>=0.6.0 \
    ta>=0.11.0 \
    || true

# Copy test files
COPY tests/ ./tests/

# Copy configuration files
COPY .env.example ./.env.example
COPY pyproject.toml ./

# Set ownership
RUN chown -R trading:trading /app /opt/venv

# Switch to non-root user
USER trading

# Expose port for API
EXPOSE 8000

# Default command for development
CMD ["pytest", "tests/", "-v", "--tb=short"]

# -----------------------------------------------------------------------------
# Stage 4: Production
# -----------------------------------------------------------------------------
FROM base AS production

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only necessary application files
COPY --from=builder /app/src /app/src
COPY pyproject.toml /app/

# Install the package in production mode
WORKDIR /app
RUN pip install --no-deps -e .

# Set ownership
RUN chown -R trading:trading /app

# Switch to non-root user
USER trading

# Expose port for API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Build arguments for version labeling
ARG VERSION=latest
ARG BUILD_DATE
ARG VCS_REF

# Labels following OCI specification
LABEL org.opencontainers.image.title="Reasoning Trading" \
      org.opencontainers.image.description="MCTS-Enhanced Multi-Agent Trading Framework" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="Reasoning Trading" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/ianshank/Reasoning-Trading"

# Default command - run the API server
CMD ["uvicorn", "reasoning_trading.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
