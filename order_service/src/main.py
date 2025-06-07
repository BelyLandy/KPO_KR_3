from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI

from src.dependencies import Container
from src.infra.data.base import Base
from src.infra.data.database import get_engine
from src.routes import router as order_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекстный менеджер жизненного цикла приложения:
    1. Инициализация и миграция БД.
    2. Запуск Kafka consumer и outbox publisher.
    3. Плавная остановка задач и ресурсов.
    """
    # Подключаемся к БД и создаём таблицы
    engine = get_engine("postgresql+asyncpg://user:password@orders_db:5432/order_db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Берём зависимости из контейнера
    publisher = app.container.outbox_publisher()
    consumer = app.container.consumer()

    # Стартуем consumer и publisher
    await consumer.start()
    publisher_task = asyncio.create_task(publisher.run())
    consumer_task = asyncio.create_task(consumer.poll_and_process(handler))

    try:
        yield
    finally:
        # Отменяем фоновые задачи
        consumer_task.cancel()
        publisher_task.cancel()
        await asyncio.gather(consumer_task, publisher_task, return_exceptions=True)

        # Завершаем consumer и закрываем движок
        await consumer.stop()
        await engine.dispose()


def create_app() -> FastAPI:
    """
    Конфигурирует и возвращает FastAPI приложение с DI-контейнером и роутами.
    """
    container = Container()
    app = FastAPI(title="Orders Service", lifespan=lifespan)
    app.container = container
    app.include_router(order_router, prefix="/orders", tags=["Orders"])
    return app


app = create_app()


async def handler(msg):
    """
    Простейший обработчик сообщений из Kafka.
    """
    print(f"Received message: {msg.value.decode()}")
