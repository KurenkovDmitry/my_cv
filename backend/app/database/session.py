"""Фасад инициализации SQLAlchemy engine и session factory."""

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Literal, Protocol

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import get_settings

DatabaseAccessMode = Literal["read", "write", "admin"]


class DatabaseSessionFactory(Protocol):
    """Интерфейс фабрики асинхронных сессий БД."""

    async def __call__(self) -> AsyncIterator[AsyncSession]:
        ...


def _build_engine(database_url: str) -> AsyncEngine:
    """Создаёт async engine с единым набором безопасных опций."""

    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache(maxsize=1)
def get_read_database_engine() -> AsyncEngine:
    """Создаёт и кэширует async engine для read-only роли."""

    settings = get_settings()
    return _build_engine(settings.database_read_url)


@lru_cache(maxsize=1)
def get_write_database_engine() -> AsyncEngine:
    """Создаёт и кэширует async engine для write-роли."""

    settings = get_settings()
    return _build_engine(settings.database_write_url)


@lru_cache(maxsize=1)
def get_admin_database_engine() -> AsyncEngine:
    """Создаёт и кэширует async engine для admin-роли."""

    settings = get_settings()
    return _build_engine(settings.database_admin_url)


def get_database_engine(access_mode: DatabaseAccessMode = "write") -> AsyncEngine:
    """Возвращает engine нужного уровня доступа."""

    if access_mode == "read":
        return get_read_database_engine()

    if access_mode == "admin":
        return get_admin_database_engine()

    return get_write_database_engine()


@lru_cache(maxsize=1)
def get_read_session_maker() -> async_sessionmaker[AsyncSession]:
    """Фабрика SQLAlchemy-сессий для read-only операций."""

    return async_sessionmaker(
        bind=get_read_database_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


@lru_cache(maxsize=1)
def get_write_session_maker() -> async_sessionmaker[AsyncSession]:
    """Фабрика SQLAlchemy-сессий для write-операций."""

    return async_sessionmaker(
        bind=get_write_database_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


@lru_cache(maxsize=1)
def get_admin_session_maker() -> async_sessionmaker[AsyncSession]:
    """Фабрика SQLAlchemy-сессий для миграций, grant-sync и админских сервисных операций."""

    return async_sessionmaker(
        bind=get_admin_database_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


def get_database_session_maker(access_mode: DatabaseAccessMode = "write") -> async_sessionmaker[AsyncSession]:
    """Возвращает session-maker нужного уровня доступа."""

    if access_mode == "read":
        return get_read_session_maker()

    if access_mode == "admin":
        return get_admin_session_maker()

    return get_write_session_maker()


async def get_read_database_session() -> AsyncIterator[AsyncSession]:
    """Открывает read-only сессию БД для публичных read-path операций."""

    session_maker = get_read_session_maker()
    async with session_maker() as session:
        yield session


async def get_write_database_session() -> AsyncIterator[AsyncSession]:
    """Открывает write-сессию БД для mutation-path операций."""

    session_maker = get_write_session_maker()
    async with session_maker() as session:
        yield session


async def get_admin_database_session() -> AsyncIterator[AsyncSession]:
    """Открывает admin-сессию БД для миграций, partition-management и grant-refresh задач."""

    session_maker = get_admin_session_maker()
    async with session_maker() as session:
        yield session


async def get_database_session() -> AsyncIterator[AsyncSession]:
    """Совместимый alias. По умолчанию открывает write-сессию БД."""

    async for session in get_write_database_session():
        yield session
