from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import OffsetAndMetadata, TopicPartition

from src.infra.postgres_repository import PostgresRepository


class Consumer:
    """ Консюмер Kafka, который читает сообщения и сохраняет их в таблицу inbox. """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        transactional_id: str,
        repository: PostgresRepository
    ) -> None:
        self._topic = topic
        self._group_id = group_id
        self._repo = repository

        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=False,
            isolation_level="read_committed"
        )
        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            transactional_id=transactional_id,
            enable_idempotence=True
        )

    async def start(self) -> None:
        """ Запустить Kafka consumer и producer. """
        await self._consumer.start()
        await self._producer.start()

    async def stop(self) -> None:
        """ Остановить consumer и producer. """
        await self._consumer.stop()
        await self._producer.stop()

    async def poll_and_process(self, handler) -> None:
        """ Циклически опрашивает топик, обрабатывает сообщения через handler и сохраняет их в payment_inbox. """
        while True:
            batch = await self._consumer.getmany(timeout_ms=1000)
            if not batch:
                continue

            await self._producer.begin_transaction()
            try:
                for tp, messages in batch.items():
                    for message in messages:
                        await handler(message)
                        decoded = message.value.decode()
                        await self._repo.insert_payment_inbox(decoded)

                offsets = {
                    tp: OffsetAndMetadata(msgs[-1].offset + 1, "")
                    for tp, msgs in batch.items()
                }
                await self._producer.send_offsets_to_transaction(offsets, self._group_id)
                await self._producer.commit_transaction()
            except Exception as exc:
                await self._producer.abort_transaction()
                print(f"[ERROR] transaction aborted: {exc}")
