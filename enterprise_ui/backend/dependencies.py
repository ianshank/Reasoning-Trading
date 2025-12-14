"""
FastAPI dependency injection for services and resources.

Provides singleton instances of services, database connections,
Redis cache, and authentication dependencies for route handlers.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from enterprise_ui.backend.config import BackendSettings, get_backend_settings
from enterprise_ui.backend.core.logging import get_logger
from reasoning_trading.agents.coordinator import MultiAgentTradingMCTS
from reasoning_trading.config import get_settings
from reasoning_trading.core.actions import ActionSpace

logger = get_logger(__name__)

# Security schemes
security = HTTPBearer()


# --- Configuration Dependencies ---


def get_settings_dependency() -> BackendSettings:
    """
    Get backend settings dependency.

    Returns:
        BackendSettings instance

    Example:
        @app.get("/config")
        async def get_config(settings: Annotated[BackendSettings, Depends(get_settings_dependency)]):
            return {"environment": settings.environment}
    """
    return get_backend_settings()


# --- Database Dependencies ---


@lru_cache
def get_async_engine():
    """
    Get SQLAlchemy async engine (cached singleton).

    Returns:
        AsyncEngine instance
    """
    settings = get_backend_settings()

    # Convert sqlite:/// to sqlite+aiosqlite:///
    db_url = settings.database.url
    if db_url.startswith("sqlite:///"):
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    return create_async_engine(
        db_url,
        echo=settings.database.echo,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
    )


@lru_cache
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Get SQLAlchemy async session maker (cached singleton).

    Returns:
        async_sessionmaker instance
    """
    engine = get_async_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency.

    Yields:
        AsyncSession instance

    Example:
        @app.get("/users")
        async def get_users(db: Annotated[AsyncSession, Depends(get_db_session)]):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# --- Redis Dependencies ---


_redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    """
    Get Redis client dependency (singleton).

    Returns:
        Redis client instance

    Example:
        @app.get("/cache")
        async def get_cache(redis: Annotated[Redis, Depends(get_redis_client)]):
            value = await redis.get("key")
            return {"value": value}
    """
    global _redis_client

    if _redis_client is None:
        settings = get_backend_settings()
        _redis_client = Redis.from_url(
            settings.core.cache.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("redis_client_initialized", url=settings.core.cache.redis_url)

    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("redis_client_closed")


# --- Service Dependencies ---


@lru_cache
def get_multi_agent_mcts() -> MultiAgentTradingMCTS:
    """
    Get MultiAgentTradingMCTS coordinator (cached singleton).

    Returns:
        MultiAgentTradingMCTS instance

    Example:
        @app.post("/analyze")
        async def analyze(
            coordinator: Annotated[MultiAgentTradingMCTS, Depends(get_multi_agent_mcts)]
        ):
            result = await coordinator.analyze(state)
            return result
    """
    settings = get_settings()
    coordinator = MultiAgentTradingMCTS(settings=settings)
    logger.info("multi_agent_mcts_initialized", num_agents=len(coordinator.agents))
    return coordinator


@lru_cache
def get_action_space() -> ActionSpace:
    """
    Get ActionSpace for MCTS (cached singleton).

    Returns:
        ActionSpace instance configured from settings

    Example:
        @app.get("/actions/sample")
        async def sample_action(
            action_space: Annotated[ActionSpace, Depends(get_action_space)]
        ):
            action = action_space.sample_action()
            return action.to_dict()
    """
    settings = get_settings()
    action_space = ActionSpace(
        allow_shorts=settings.features.allow_shorts,
        max_position_size=settings.risk.max_position_size_fraction,
        progressive_widening_alpha=settings.mcts.progressive_widening_alpha,
    )
    logger.info("action_space_initialized", allow_shorts=settings.features.allow_shorts)
    return action_space


# --- Authentication Dependencies ---


async def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security)],
    settings: Annotated[BackendSettings, Depends(get_settings_dependency)],
) -> dict:
    """
    Verify JWT token from Authorization header.

    Args:
        credentials: HTTP authorization credentials
        settings: Backend settings

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired

    Example:
        @app.get("/protected")
        async def protected_route(
            token_data: Annotated[dict, Depends(verify_token)]
        ):
            return {"user": token_data["sub"]}
    """
    try:
        import jwt

        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.jwt.secret_key.get_secret_value(),
            algorithms=[settings.jwt.algorithm],
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError as e:
        logger.warning("invalid_token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token_data: Annotated[dict, Depends(verify_token)],
) -> str:
    """
    Get current authenticated user from token.

    Args:
        token_data: Decoded token payload

    Returns:
        User identifier (username or user ID)

    Example:
        @app.get("/me")
        async def get_me(
            current_user: Annotated[str, Depends(get_current_user)]
        ):
            return {"username": current_user}
    """
    username = token_data.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    return username


# Optional authentication (allows anonymous access)
async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security, auto_error=False),
) -> str | None:
    """
    Get current user if authenticated, None otherwise.

    Allows endpoints to be accessible both authenticated and anonymously.

    Args:
        credentials: Optional HTTP authorization credentials

    Returns:
        User identifier or None

    Example:
        @app.get("/public-or-private")
        async def hybrid_endpoint(
            user: Annotated[str | None, Depends(get_optional_user)]
        ):
            if user:
                return {"message": f"Hello {user}"}
            return {"message": "Hello anonymous"}
    """
    if credentials is None:
        return None

    try:
        settings = get_backend_settings()
        import jwt

        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.jwt.secret_key.get_secret_value(),
            algorithms=[settings.jwt.algorithm],
        )
        return payload.get("sub")
    except jwt.JWTError:
        return None


# Type aliases for cleaner annotations
BackendSettingsDep = Annotated[BackendSettings, Depends(get_settings_dependency)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
RedisDep = Annotated[Redis, Depends(get_redis_client)]
MultiAgentMCTSDep = Annotated[MultiAgentTradingMCTS, Depends(get_multi_agent_mcts)]
ActionSpaceDep = Annotated[ActionSpace, Depends(get_action_space)]
CurrentUserDep = Annotated[str, Depends(get_current_user)]
OptionalUserDep = Annotated[str | None, Depends(get_optional_user)]
