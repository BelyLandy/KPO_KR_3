import importlib
import pytest
from unittest.mock import MagicMock
from dependency_injector import providers


@pytest.fixture(autouse=True)
def patch_external(monkeypatch):
    """
    Избегаем реальных зависимостей БД и Kafka:
    – мокаем get_engine/get_session_maker в модуле data,
    – мокаем AIOKafkaConsumer и AIOKafkaProducer в модуле consumer,
    и перезагружаем контейнер.
    """
    # патч data
    db_mod = importlib.import_module("src.infra.data.database")
    importlib.reload(db_mod)
    monkeypatch.setattr(db_mod, "get_engine", lambda **kw: MagicMock(name="Engine"))
    monkeypatch.setattr(db_mod, "get_session_maker", lambda **kw: (lambda: MagicMock(name="Session")))

    # патч consumer
    cons_mod = importlib.import_module("src.infra.services.consumer")
    monkeypatch.setattr(cons_mod, "AIOKafkaConsumer", MagicMock(name="AIOKafkaConsumer"))
    monkeypatch.setattr(cons_mod, "AIOKafkaProducer", MagicMock(name="AIOKafkaProducer"))

    # перезагружаем контейнер
    deps_mod = importlib.import_module("src.dependencies")
    importlib.reload(deps_mod)


@pytest.fixture
def container():
    """
    Возвращает DI-контейнер, где все внешние провайдеры заменены на моки.
    """
    from src.dependencies import Container

    container = Container()
    container.producer.override(providers.Singleton(MagicMock(name="Producer")))
    container.db_engine.override(providers.Singleton(MagicMock(name="Engine")))
    container.session_factory.override(providers.Singleton(MagicMock(name="SessionFactory")))
    container.db_session.override(providers.Factory(lambda: MagicMock(name="Session")))

    repo_mock = MagicMock(name="Repository")
    container.order_repository.override(providers.Object(repo_mock))

    yield container
    container.unwire()


def test_producer_is_singleton(container):
    assert container.producer() is container.producer()


def test_order_service_is_factory(container):
    assert container.order_service() is not container.order_service()


def test_db_session_is_factory(container):
    assert container.db_session() is not container.db_session()


def test_order_service_receives_repository(container):
    from src.infra.services.order_service import OrderService
    svc = container.order_service()
    # заинжекченный репозиторий лежит в private _repository
    assert svc._repository is container.order_repository()


def test_outbox_publisher_singleton_and_injection(container):
    from src.infra.services.outbox_publisher import OutboxPublisher
    pub1 = container.outbox_publisher()
    pub2 = container.outbox_publisher()
    assert pub1 is pub2 and isinstance(pub1, OutboxPublisher)
    # репозиторий хранится в private _repository
    assert pub1._repository is container.order_repository()


def test_consumer_singleton_and_injection(container):
    from src.infra.services.consumer import Consumer
    c1 = container.consumer()
    c2 = container.consumer()
    assert c1 is c2 and isinstance(c1, Consumer)
    # Consumer по-прежнему имеет public .repository
    assert c1.repository is container.order_repository()
