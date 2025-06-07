from dependency_injector import containers, providers

from src.infra.data.database import get_engine, get_session_maker
from src.infra.postgres_repository import PostgresRepository
from src.infra.services.payment_service import PaymentService
from src.infra.services.consumer import Consumer
from src.infra.services.producer import Producer
from src.infra.services.worker_service import Worker
from src.infra.services.outbox_publisher import OutboxPublisher


class Container(containers.DeclarativeContainer):
    """
    DI-контейнер для Payment Service:
    настраивает Kafka, БД, репозитории и сервисы.
    """
    wiring_config = containers.WiringConfiguration(
        modules=["src.routes"]
    )

    # Kafka Producer с транзакциями
    kafka_producer = providers.Singleton(
        Producer,
        bootstrap_servers="broker:9092",
        transactional_id="payment_status_transactional_id",
    )

    # Асинхронный движок базы данных
    db_engine = providers.Singleton(
        get_engine,
        database_url="postgresql+asyncpg://user:password@payments_db:5432/payment_db",
    )

    # Фабрика асинхронных сессий SQLAlchemy
    session_factory = providers.Singleton(
        get_session_maker,
        engine=db_engine,
    )

    # Каждый вызов дает новую сессию
    db_session = providers.Factory(
        lambda session_factory=session_factory(): session_factory()
    )

    # Репозиторий для операций с платежами
    payment_repository = providers.Factory(
        PostgresRepository,
        session=db_session,
    )

    # Бизнес-сервис для работы с аккаунтами и платежами
    payment_service = providers.Factory(
        PaymentService,
        repository=payment_repository,
    )

    # Kafka Consumer для обработки событий заказов
    kafka_consumer = providers.Singleton(
        Consumer,
        bootstrap_servers="broker:9092",
        topic="order",
        group_id="payment_service_group",
        transactional_id="payment_service_transactional_id",
        repository=payment_repository,
    )

    # Фоновый воркер для обработки inbox-событий
    worker_service = providers.Singleton(
        Worker,
        repository=payment_repository,
    )

    # Публикатор из outbox в Kafka
    outbox_publisher = providers.Singleton(
        OutboxPublisher,
        broker=kafka_producer,
        repository=payment_repository,
    )
