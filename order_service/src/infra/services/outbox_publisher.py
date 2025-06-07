import asyncio
import json
from typing import Optional

from src.infra.postgres_repository import PostgresRepository
from src.infra.services.producer import Producer


class OutboxPublisher:
    """
    Публикует события из таблицы outbox в Kafka через Producer.
    """

    def __init__(
        self,
        repository: PostgresRepository,
        broker: Producer
    ) -> None:
        """
        :param repository: Репозиторий для доступа к данным outbox
        :param broker: Kafka-продюсер для отправки сообщений
        """
        self._repository = repository
        self._broker = broker

    async def _publish_pending(self) -> None:
        """
        Читает все необработанные записи из outbox,
        отправляет их в Kafka и помечает как обработанные.
        """
        pending = await self._repository.get_orders_outbox()
        for record in pending:
            payload_bytes = json.dumps(record.payload).encode("utf-8")
            await self._broker.send(topic="order", key=None, value=payload_bytes)
            await self._repository.update_outbox_order_status(record.id)

    async def run(
        self,
        interval: Optional[int] = 2
    ) -> None:
        """
        Запускает бесконечный цикл: каждую interval секунды
        публикует все новые события и при завершении останавливает продюсер.

        :param interval: Интервал между проверками (в секундах)
        """
        await self._broker.start()
        try:
            while True:
                await asyncio.sleep(interval)
                await self._publish_pending()
        finally:
            await self._broker.stop()
