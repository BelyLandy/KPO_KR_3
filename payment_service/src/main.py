from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

from src.dependencies import Container
from src.infra.data.base import Base
from src.infra.data.database import get_engine
from src.routes import router as accounts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """ Настройка и очистка ресурсов при старте/остановке приложения. """

    engine = get_engine("postgresql+asyncpg://user:password@payments_db:5432/payment_db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    consumer = app.container.kafka_consumer()
    await consumer.start()

    worker = app.container.worker_service()
    publisher = app.container.outbox_publisher()

    consumer_task = asyncio.create_task(consumer.poll_and_process(handler))
    worker_task = asyncio.create_task(worker.run())
    publisher_task = asyncio.create_task(publisher.run())

    try:
        yield
    finally:
        consumer_task.cancel()
        worker_task.cancel()
        publisher_task.cancel()

        await asyncio.gather(
            consumer_task,
            worker_task,
            publisher_task,
            return_exceptions=True
        )

        await consumer.stop()
        await engine.dispose()


def create_app() -> FastAPI:
    """ Создает и настраивает FastAPI-приложение с DI-контейнером и роутами. """
    container = Container()
    app = FastAPI(title="Payments Service", lifespan=lifespan)
    app.container = container
    app.include_router(accounts_router, prefix="/accounts", tags=["Accounts"])
    return app


app = create_app()


async def handler(msg):
    """ Простейший обработчик Kafka-сообщений. """
    print(f"Received message: {msg.value.decode()}")
