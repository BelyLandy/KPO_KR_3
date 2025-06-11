import pytest
import json
from aiokafka.structs import OffsetAndMetadata, TopicPartition
from unittest.mock import AsyncMock, MagicMock, patch

from src.infra.services.consumer import Consumer


@pytest.mark.asyncio
async def test_start_and_stop():
    fake_consumer = AsyncMock(start=AsyncMock(), stop=AsyncMock())
    fake_producer = AsyncMock(start=AsyncMock(), stop=AsyncMock())

    with patch("src.infra.services.consumer.AIOKafkaConsumer", return_value=fake_consumer), \
         patch("src.infra.services.consumer.AIOKafkaProducer", return_value=fake_producer):
        c = Consumer(
            bootstrap_servers="srv:9092",
            topic="t",
            group_id="g",
            transactional_id="tx",
            repository=AsyncMock()
        )

        await c.start()
        fake_consumer.start.assert_awaited_once()
        fake_producer.start.assert_awaited_once()

        await c.stop()
        fake_consumer.stop.assert_awaited_once()
        fake_producer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_and_process_success():
    payload1 = {"order_id": "o1", "user_id": "u1", "amount": "10.00"}
    payload2 = {"order_id": "o2", "user_id": "u2", "amount": "20.00"}

    msg1 = MagicMock(value=json.dumps(payload1).encode(), offset=0)
    msg2 = MagicMock(value=json.dumps(payload2).encode(), offset=5)

    sequence = [
        {TopicPartition("topic", 0): [msg1, msg2]},
        StopAsyncIteration
    ]
    fake_consumer = AsyncMock(getmany=AsyncMock(side_effect=iter(sequence)))
    fake_consumer.start, fake_consumer.stop = AsyncMock(), AsyncMock()

    fake_producer = AsyncMock(
        begin_transaction=AsyncMock(),
        send_offsets_to_transaction=AsyncMock(),
        commit_transaction=AsyncMock(),
        abort_transaction=AsyncMock(),
        start=AsyncMock(),
        stop=AsyncMock()
    )

    mock_repo = AsyncMock(insert_payment_inbox=AsyncMock())
    handler = AsyncMock()

    with patch("src.infra.services.consumer.AIOKafkaConsumer", return_value=fake_consumer), \
         patch("src.infra.services.consumer.AIOKafkaProducer", return_value=fake_producer):
        c = Consumer("srv", "topic", "grp", "txid", mock_repo)
        await c.start()

        with pytest.raises(StopAsyncIteration):
            await c.poll_and_process(handler)

        handler.assert_any_await(msg1)
        handler.assert_any_await(msg2)

        mock_repo.insert_payment_inbox.assert_any_await(json.dumps(payload1))
        mock_repo.insert_payment_inbox.assert_any_await(json.dumps(payload2))

        fake_producer.begin_transaction.assert_awaited_once()
        expected_offsets = {
            TopicPartition("topic", 0): OffsetAndMetadata(msg2.offset + 1, "")
        }
        fake_producer.send_offsets_to_transaction.assert_awaited_once_with(expected_offsets, "grp")
        fake_producer.commit_transaction.assert_awaited_once()
        fake_producer.abort_transaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_poll_and_process_handler_error_aborts():
    msg = MagicMock(value=b"{}", offset=2)
    sequence = [{TopicPartition("t", 0): [msg]}, StopAsyncIteration]
    fake_consumer = AsyncMock(getmany=AsyncMock(side_effect=iter(sequence)))
    fake_consumer.start, fake_consumer.stop = AsyncMock(), AsyncMock()

    fake_producer = AsyncMock(
        begin_transaction=AsyncMock(),
        send_offsets_to_transaction=AsyncMock(),
        commit_transaction=AsyncMock(),
        abort_transaction=AsyncMock(),
        start=AsyncMock(),
        stop=AsyncMock()
    )

    async def bad_handler(_):
        raise RuntimeError("oops")

    mock_repo = AsyncMock(insert_payment_inbox=AsyncMock())

    with patch("src.infra.services.consumer.AIOKafkaConsumer", return_value=fake_consumer), \
         patch("src.infra.services.consumer.AIOKafkaProducer", return_value=fake_producer):
        c = Consumer("b", "t", "g", "tx", mock_repo)
        await c.start()

        with pytest.raises(StopAsyncIteration):
            await c.poll_and_process(bad_handler)

        fake_producer.begin_transaction.assert_awaited_once()
        fake_producer.abort_transaction.assert_awaited_once()
        fake_producer.commit_transaction.assert_not_awaited()

        mock_repo.insert_payment_inbox.assert_not_awaited()


@pytest.mark.asyncio
async def test_poll_and_process_repo_error_aborts_and_logs(capsys):
    payload = {"order_id": "x", "user_id": "y", "amount": "5.00"}
    msg = MagicMock(value=json.dumps(payload).encode(), offset=1)
    sequence = [{TopicPartition("tp", 0): [msg]}, StopAsyncIteration]
    fake_consumer = AsyncMock(getmany=AsyncMock(side_effect=iter(sequence)))
    fake_consumer.start, fake_consumer.stop = AsyncMock(), AsyncMock()

    fake_producer = AsyncMock(
        begin_transaction=AsyncMock(),
        send_offsets_to_transaction=AsyncMock(),
        commit_transaction=AsyncMock(),
        abort_transaction=AsyncMock(),
        start=AsyncMock(),
        stop=AsyncMock()
    )

    async def repo_fail(arg):
        raise RuntimeError("DB fail")
    mock_repo = AsyncMock(insert_payment_inbox=AsyncMock(side_effect=repo_fail))

    handler = AsyncMock()

    with patch("src.infra.services.consumer.AIOKafkaConsumer", return_value=fake_consumer), \
         patch("src.infra.services.consumer.AIOKafkaProducer", return_value=fake_producer):
        c = Consumer("srv", "tp", "grp", "tx", mock_repo)
        await c.start()

        with pytest.raises(StopAsyncIteration):
            await c.poll_and_process(handler)

        fake_producer.begin_transaction.assert_awaited_once()
        fake_producer.abort_transaction.assert_awaited_once()
        fake_producer.commit_transaction.assert_not_awaited()

        captured = capsys.readouterr()
        assert "[ERROR] transaction aborted: DB fail" in captured.out


@pytest.mark.asyncio
async def test_poll_and_process_skips_empty_batches():
    fake_consumer = AsyncMock(getmany=AsyncMock(side_effect=[{}, StopAsyncIteration]))
    fake_consumer.start, fake_consumer.stop = AsyncMock(), AsyncMock()
    fake_producer = AsyncMock(
        begin_transaction=AsyncMock(),
        send_offsets_to_transaction=AsyncMock(),
        commit_transaction=AsyncMock(),
        abort_transaction=AsyncMock(),
        start=AsyncMock(),
        stop=AsyncMock()
    )
    mock_repo = AsyncMock(insert_payment_inbox=AsyncMock())
    handler = AsyncMock()

    with patch("src.infra.services.consumer.AIOKafkaConsumer", return_value=fake_consumer), \
         patch("src.infra.services.consumer.AIOKafkaProducer", return_value=fake_producer):
        c = Consumer("s", "t", "g", "tx", mock_repo)
        await c.start()

        with pytest.raises(StopAsyncIteration):
            await c.poll_and_process(handler)

        handler.assert_not_awaited()
        mock_repo.insert_payment_inbox.assert_not_awaited()
        fake_producer.begin_transaction.assert_not_awaited()
        fake_producer.commit_transaction.assert_not_awaited()
        fake_producer.abort_transaction.assert_not_awaited()
