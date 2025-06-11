import json

import uuid
import pytest

from unittest.mock import AsyncMock, MagicMock, patch
from aiokafka.structs import TopicPartition

from src.infra.services.consumer import Consumer


@pytest.mark.asyncio
async def test_poll_and_process_success():
    """ Проверяет успешную обработку нескольких сообщений. """
    payload1 = {"order_id": str(uuid.uuid4()), "status": "FINISHED"}
    payload2 = {"order_id": str(uuid.uuid4()), "status": "CANCELED"}

    msg1 = MagicMock(offset=5, value=json.dumps(payload1).encode("utf-8"))
    msg2 = MagicMock(offset=6, value=json.dumps(payload2).encode("utf-8"))

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

        await consumer.start()

        with pytest.raises(StopAsyncIteration):
            await consumer.poll_and_process(handler)

        handler.assert_any_await(msg1)
        handler.assert_any_await(msg2)

        mock_repo.update_order_status.assert_any_await(
            payload1["order_id"], payload1["status"]
        )
        mock_repo.update_order_status.assert_any_await(
            payload2["order_id"], payload2["status"]
        )

        fake_producer.begin_transaction.assert_awaited()
        fake_producer.send_offsets_to_transaction.assert_awaited()
        fake_producer.commit_transaction.assert_awaited()

        await consumer.stop()


@pytest.mark.asyncio
async def test_poll_and_process_handler_error_aborts():
    """ Проверяет, что при ошибке в handler. """
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

        fake_producer.abort_transaction.assert_awaited()
        fake_producer.commit_transaction.assert_not_awaited()

        await consumer.stop()
