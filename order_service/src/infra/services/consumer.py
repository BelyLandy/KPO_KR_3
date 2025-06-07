import json
from typing import Callable, Awaitable, Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import OffsetAndMetadata, TopicPartition

from src.infra.postgres_repository import PostgresRepository


class Consumer:
    """
    Консюмер для обработки событий из Kafka и обновления статуса заказов в БД.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        transactional_id: str,
        repository: PostgresRepository,
    ) -> None:
        """
        :param bootstrap_servers: Адрес(а) Kafka-брокера
        :param topic: Топик для чтения сообщений
        :param group_id: Идентификатор группы консюмеров
        :param transactional_id: Идентификатор транзакции продьюсера
        :param repository: Репозиторий для работы с заказами
        """
        self._topic = topic
        self._group_id = group_id
        self.repository = repository

        # Консюмер без автокоммита, с уровнем изоляции read_committed
        self._consumer: AIOKafkaConsumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=False,
            isolation_level="read_committed",
        )

        # Продьюсер для управления оффсетами в транзакции
        self._producer: AIOKafkaProducer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            transactional_id=transactional_id,
            enable_idempotence=True,
        )

    async def start(self) -> None:
        """Запуск консюмера и продьюсера."""
        await self._consumer.start()
        await self._producer.start()

    async def stop(self) -> None:
        """Остановка консюмера и продьюсера."""
        await self._consumer.stop()
        await self._producer.stop()

    async def poll_and_process(
        self,
        handler: Callable[[Any], Awaitable[None]],
    ) -> None:
        """
        Бессрочный цикл опроса Kafka, обработки и коммита в транзакции.

        :param handler: Асинхронная функция-обработчик отдельного сообщения.
        """
        while True:
            # Получаем пачку записей из всех партиций
            records = await self._consumer.getmany(timeout_ms=1000)
            if not records:
                continue

            # Начинаем транзакцию в продьюсере
            await self._producer.begin_transaction()
            try:
                # Обработка каждого сообщения
                for tp, msgs in records.items():
                    for msg in msgs:
                        await handler(msg)
                        payload = json.loads(msg.value.decode())
                        # Обновляем статус заказа в БД
                        await self.repository.update_order_status(
                            payload["order_id"],
                            payload["status"],
                        )

                # Формируем оффсеты для коммита
                offsets: dict[TopicPartition, OffsetAndMetadata] = {
                    tp: OffsetAndMetadata(msgs[-1].offset + 1, "")
                    for tp, msgs in records.items()
                }

                # Отправляем оффсеты как часть транзакции
                await self._producer.send_offsets_to_transaction(
                    offsets, self._group_id
                )
                await self._producer.commit_transaction()

            except Exception as e:
                # При ошибке откатываем транзакцию и логируем
                await self._producer.abort_transaction()
                print(f"[ERROR] Transaction aborted: {e}")
