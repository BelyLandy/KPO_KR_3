from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncEngine

from src.infra.data.database import get_engine, get_session_maker
from src.infra.postgres_repository import PostgresRepository
from src.infra.services.producer import Producer
from src.infra.services.consumer import Consumer
from src.infra.services.outbox_publisher import OutboxPublisher
from src.infra.services.order_service import OrderService


class Container(containers.DeclarativeContainer):
    """
    DI-контейнер для настройки всех зависимостей приложения.
    """
    wiring_config = containers.WiringConfiguration(modules=["src.routes"])

    # --- Kafka Producer с транзакционным идемпотентным продьюсером ---
    producer: providers.Singleton[Producer] = providers.Singleton(
        Producer,
        bootstrap_servers="broker:9092",
        transactional_id="order_service_transactional_id",
    )

    # --- Асинхронный движок Postgres ---
    db_engine: providers.Singleton[AsyncEngine] = providers.Singleton(
        get_engine,
        database_url="postgresql+asyncpg://user:password@orders_db:5432/order_db",
    )

    # --- Фабрика AsyncSession ---
    session_factory = providers.Singleton(
        get_session_maker,
        engine=db_engine,
    )

    # --- Каждая сессия — новый экземпляр AsyncSession ---
    db_session = providers.Factory(
        lambda session_factory=session_factory(): session_factory()
    )

    # --- Репозиторий для работы с заказами ---
    order_repository = providers.Factory(
        PostgresRepository,
        session=db_session,
    )

    # --- Сервис бизнес-логики заказов ---
    order_service = providers.Factory(
        OrderService,
        repository=order_repository,
    )

    # --- Публишер записей из outbox в Kafka ---
    outbox_publisher = providers.Singleton(
        OutboxPublisher,
        repository=order_repository,
        broker=producer,
    )

    # --- Kafka Consumer для обработки событий платежей ---
    consumer = providers.Singleton(
        Consumer,
        bootstrap_servers="broker:9092",
        topic="payments",
        group_id="payment_status_group",
        transactional_id="order_status_transactional_id",
        repository=order_repository,
    )
