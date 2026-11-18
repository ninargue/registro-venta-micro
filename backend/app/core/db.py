import uuid
from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.security import CurrentUser, get_current_tenant, get_current_user


@lru_cache
def get_engine() -> AsyncEngine:
    """Crea y cachea el motor async de SQLAlchemy con NullPool y statement_cache_size."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
        connect_args={"statement_cache_size": settings.db_pool_statement_cache_size},
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Devuelve la fábrica de sesiones async."""
    return async_sessionmaker(
        get_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def set_rls_user_context(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Fija el rol runtime app_api y app.current_user_id en la transacción actual."""
    await session.execute(text("SET LOCAL ROLE app_api"))
    await session.execute(
        text("SELECT set_config('app.current_user_id', :user_id, true)"),
        {"user_id": str(user_id)},
    )


async def set_rls_business_context(session: AsyncSession, business_id: uuid.UUID) -> None:
    """Fija app.current_business_id en la transacción actual."""
    await session.execute(
        text("SELECT set_config('app.current_business_id', :business_id, true)"),
        {"business_id": str(business_id)},
    )


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Provee una sesión async sin contexto RLS previo (el caso de uso abre su transacción)."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def get_user_db(
    current_user: CurrentUser = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession]:
    """Abre transacción bajo app_api con app.current_user_id configurado."""
    session_factory = get_session_factory()
    async with session_factory() as session, session.begin():
        await set_rls_user_context(session, current_user.user_id)
        yield session


async def get_tenant_db(
    current_user: CurrentUser = Depends(get_current_tenant),
) -> AsyncGenerator[AsyncSession]:
    """Abre transacción bajo app_api con app.current_user_id y app.current_business_id."""
    assert current_user.business_id is not None
    session_factory = get_session_factory()
    async with session_factory() as session, session.begin():
        await set_rls_user_context(session, current_user.user_id)
        await set_rls_business_context(session, current_user.business_id)
        yield session
