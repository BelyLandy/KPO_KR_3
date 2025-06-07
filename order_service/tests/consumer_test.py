import json

import uuid
import pytest

from unittest.mock import AsyncMock, MagicMock, patch
from aiokafka.structs import TopicPartition

from src.infra.services.consumer import Consumer


@pytest.mark.asyncio
async def test_poll_and_process_success():
    """
    Проверяет успешную обработку нескольких сообщений:
    - вызов handler для каждого сообщения
    - обновление статуса заказа в репозитории
    - коммит транзакции в продюсере
    """
    # Подготовка двух сообщений с разными статусами
    payload1 = {"order_id": str(uuid.uuid4()), "status": "FINISHED"}
    payload2 = {"order_id": str(uuid.uuid4()), "status": "CANCELED"}

    msg1 = MagicMock(offset=5, value=json.dumps(payload1).encode("utf-8"))
    msg2 = MagicMock(offset=6, value=json.dumps(payload2).encode("utf-8"))

    # Фальшивая отдача: сначала две записи, потом пустой словарь для остановки
    records_sequence = [
        {TopicPartition("topic", 0): [msg1, msg2]},
        {}
    ]

    fake_consumer = AsyncMock()
    fake_consumer.getmany = AsyncMock(side_effect=iter(records_sequence))
    fake_consumer.start = AsyncMock()
    fake_consumer.stop = AsyncMock()

    fake_producer = AsyncMock(
        begin_transaction=AsyncMock(),
        send_offsets_to_transaction=AsyncMock(),
        commit_transaction=AsyncMock(),
        abort_transaction=AsyncMock(),
        start=AsyncMock(),
        stop=AsyncMock()
    )

    mock_repo = AsyncMock()
    handler = AsyncMock()

    # Мокаем конструкторы KafkaConsumer/Producer внутри модуля consumer
    with patch(
        "src.infra.services.consumer.AIOKafkaConsumer",
        return_value=fake_consumer
    ), patch(
        "src.infra.services.consumer.AIOKafkaProducer",
        return_value=fake_producer
    ):
        consumer = Consumer(
            bootstrap_servers="dummy:9092",
            topic="topic",
            group_id="g1",
            transactional_id="tran1",
            repository=mock_repo
        )

        # Стартуем consumer/producer
        await consumer.start()

        # Ожидаем StopAsyncIteration при пустом getmany во второй итерации
        with pytest.raises(StopAsyncIteration):
            await consumer.poll_and_process(handler)

        # Проверяем, что handler вызван для каждого сообщения
        handler.assert_any_await(msg1)
        handler.assert_any_await(msg2)

        # Проверяем обновления статуса в репозитории
        mock_repo.update_order_status.assert_any_await(
            payload1["order_id"], payload1["status"]
        )
        mock_repo.update_order_status.assert_any_await(
            payload2["order_id"], payload2["status"]
        )

        # Проверяем транзакционные вызовы продюсера
        fake_producer.begin_transaction.assert_awaited()
        fake_producer.send_offsets_to_transaction.assert_awaited()
        fake_producer.commit_transaction.assert_awaited()

        # Останавливаем consumer/producer
        await consumer.stop()


@pytest.mark.asyncio
async def test_poll_and_process_handler_error_aborts():
    """
    Проверяет, что при ошибке в handler:
    - транзакция продюсера откатывается
    - коммит не вызывается
    """
    payload = {"order_id": str(uuid.uuid4()), "status": "FINISHED"}
    msg = MagicMock(offset=1, value=json.dumps(payload).encode("utf-8"))

    records_sequence = [
        {TopicPartition("topic", 0): [msg]},
        {}
    ]

    fake_consumer = AsyncMock()
    fake_consumer.getmany = AsyncMock(side_effect=iter(records_sequence))
    fake_consumer.start = AsyncMock()
    fake_consumer.stop = AsyncMock()

    fake_producer = AsyncMock(
        begin_transaction=AsyncMock(),
        send_offsets_to_transaction=AsyncMock(),
        commit_transaction=AsyncMock(),
        abort_transaction=AsyncMock(),
        start=AsyncMock(),
        stop=AsyncMock()
    )

    # Handler, который сразу выбрасывает ошибку
    async def failing_handler(_):
        raise RuntimeError("handler failed")

    mock_repo = AsyncMock()

    with patch(
        "src.infra.services.consumer.AIOKafkaConsumer",
        return_value=fake_consumer
    ), patch(
        "src.infra.services.consumer.AIOKafkaProducer",
        return_value=fake_producer
    ):
        consumer = Consumer(
            bootstrap_servers="dummy:9092",
            topic="topic",
            group_id="g2",
            transactional_id="tran2",
            repository=mock_repo
        )

        await consumer.start()

        with pytest.raises(StopAsyncIteration):
            await consumer.poll_and_process(failing_handler)

        # Транзакция должна быть прервана, commit не вызывается
        fake_producer.abort_transaction.assert_awaited()
        fake_producer.commit_transaction.assert_not_awaited()

        await consumer.stop()
