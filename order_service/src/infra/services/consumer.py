import json
from typing import Callable, Awaitable, Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import OffsetAndMetadata, TopicPartition

from src.infra.postgres_repository import PostgresRepository


class Consumer:
    """ Консюмер для обработки событий из Kafka и обновления статуса заказов в БД. """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        transactional_id: str,
        repository: PostgresRepository,
    ) -> None:
        self._topic = topic
        self._group_id = group_id
        self.repository = repository

        self._consumer: AIOKafkaConsumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=False,
            isolation_level="read_committed",
        )

        self._producer: AIOKafkaProducer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            transactional_id=transactional_id,
            enable_idempotence=True,
        )

    async def start(self) -> None:
        """ Запуск консюмера и продьюсера. """
        await self._consumer.start()
        await self._producer.start()

    async def stop(self) -> None:
        """ Остановка консюмера и продьюсера. """
        await self._consumer.stop()
        await self._producer.stop()

    async def poll_and_process(
        self,
        handler: Callable[[Any], Awaitable[None]],
    ) -> None:
        """ Бессрочный цикл опроса Kafka, обработки и коммита в транзакции. """
        while True:
            records = await self._consumer.getmany(timeout_ms=1000)
            if not records:
                continue

            await self._producer.begin_transaction()
            try:
                for tp, msgs in records.items():
                    for msg in msgs:
                        await handler(msg)
                        payload = json.loads(msg.value.decode())

                        await self.repository.update_order_status(
                            payload["order_id"],
                            payload["status"],
                        )

                offsets: dict[TopicPartition, OffsetAndMetadata] = {
                    tp: OffsetAndMetadata(msgs[-1].offset + 1, "")
                    for tp, msgs in records.items()
                }

                await self._producer.send_offsets_to_transaction(
                    offsets, self._group_id
                )
                await self._producer.commit_transaction()

            except Exception as e:
                await self._producer.abort_transaction()
                print(f"[ERROR] Transaction aborted: {e}")
