import asyncio
import json
from typing import Any

from src.infra.postgres_repository import PostgresRepository
from src.infra.services.producer import Producer


class OutboxPublisher:
    """ Публикует незавершённые платежи из таблицы outbox в Kafka. """

    def __init__(
        self,
        repository: PostgresRepository,
        broker: Producer
    ) -> None:
        self._repository = repository
        self._broker = broker

    async def _publish_pending(self) -> None:
        """ Получает все необработанные записи из outbox, отправляет их в Kafka и помечает как обработанные. """
        pending = await self._repository.get_payments_outbox()
        for entry in pending:
            message = {**entry.payload, "status": entry.status}
            try:
                await self._broker.send(
                    topic="payments",
                    key=None,
                    value=json.dumps(message).encode("utf-8")
                )
                await self._repository.update_outbox_payment_status(entry.id)
            except Exception as exc:
                print(f"Ошибка при отправке платежа в Kafka: {exc}")

    async def run(self, interval: int = 2) -> None:
        """ Запускает бесконечный цикл, публикуя очередные платежи каждые interval секунд. """
        await self._broker.start()
        try:
            while True:
                await asyncio.sleep(interval)
                await self._publish_pending()
        finally:
            await self._broker.stop()
