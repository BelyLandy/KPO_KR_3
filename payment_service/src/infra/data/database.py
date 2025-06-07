from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)


def get_engine(database_url: str) -> AsyncEngine:
    """
    Инициализирует и возвращает асинхронный движок SQLAlchemy.

    :param database_url: Строка подключения к базе данных.
    :return: Экземпляр AsyncEngine.
    """
    return create_async_engine(
        database_url,
        echo=False,
        future=True,
    )


def get_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Создает и возвращает фабрику асинхронных сессий.

    :param engine: Асинхронный движок, к которому будут привязаны сессии.
    :return: async_sessionmaker, создающий AsyncSession с expire_on_commit=False.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
