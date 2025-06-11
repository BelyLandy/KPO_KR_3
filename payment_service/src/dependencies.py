from dependency_injector import containers, providers

from src.infra.data.database import get_engine, get_session_maker
from src.infra.postgres_repository import PostgresRepository
from src.infra.services.payment_service import PaymentService
from src.infra.services.consumer import Consumer
from src.infra.services.producer import Producer
from src.infra.services.worker_service import Worker
from src.infra.services.outbox_publisher import OutboxPublisher


class Container(containers.DeclarativeContainer):
    """ DI-контейнер для Payment Service. """
    wiring_config = containers.WiringConfiguration(
        modules=["src.routes"]
    )

    kafka_producer = providers.Singleton(
        Producer,
        bootstrap_servers="broker:9092",
        transactional_id="payment_status_transactional_id",
    )

    db_engine = providers.Singleton(
        get_engine,
        database_url="postgresql+asyncpg://user:password@payments_db:5432/payment_db",
    )

    session_factory = providers.Singleton(
        get_session_maker,
        engine=db_engine,
    )

    db_session = providers.Factory(
        lambda session_factory=session_factory(): session_factory()
    )

    payment_repository = providers.Factory(
        PostgresRepository,
        session=db_session,
    )

    payment_service = providers.Factory(
        PaymentService,
        repository=payment_repository,
    )

    kafka_consumer = providers.Singleton(
        Consumer,
        bootstrap_servers="broker:9092",
        topic="order",
        group_id="payment_service_group",
        transactional_id="payment_service_transactional_id",
        repository=payment_repository,
    )

    worker_service = providers.Singleton(
        Worker,
        repository=payment_repository,
    )

    outbox_publisher = providers.Singleton(
        OutboxPublisher,
        broker=kafka_producer,
        repository=payment_repository,
    )
