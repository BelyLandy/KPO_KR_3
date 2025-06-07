import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT_DIR)

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from src.infra.data.base import Base
from src.infra.postgres_repository import PostgresRepository


@pytest_asyncio.fixture
def event_loop():
    """
    Создает новый event loop для каждого тестового модуля.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def in_memory_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Асинхронный движок SQLite в памяти.
    Создает все таблицы перед стартом и закрывает движок после.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(
    in_memory_engine: AsyncEngine
) -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронная сессия SQLAlchemy.
    После теста делает rollback, чтобы не сохранять изменения.
    """
    maker = async_sessionmaker(
        bind=in_memory_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def repository(session: AsyncSession) -> PostgresRepository:
    """
    Фабрика PostgresRepository для доступа к методам работы с БД.
    """
    return PostgresRepository(session=session)
