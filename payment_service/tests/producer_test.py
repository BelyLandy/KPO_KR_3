import pytest
from unittest.mock import AsyncMock, patch

from src.infra.services.producer import Producer


@pytest.mark.asyncio
async def test_send_success_commits_transaction():
    """
    Проверяем, что при успешной отправке:
    1) begin_transaction вызывается,
    2) send_and_wait вызывается с правильными аргументами,
    3) commit_transaction вызывается,
    4) abort_transaction не вызывается.
    """
    fake_producer = AsyncMock()
    fake_producer.begin_transaction = AsyncMock()
    fake_producer.send_and_wait = AsyncMock()
    fake_producer.commit_transaction = AsyncMock()
    fake_producer.abort_transaction = AsyncMock()
    fake_producer.start = AsyncMock()
    fake_producer.stop = AsyncMock()

    with patch(
        "src.infra.services.producer.AIOKafkaProducer",
        return_value=fake_producer
    ):
        producer = Producer(bootstrap_servers="dummy:9092", transactional_id="tran-id")
        await producer.start()

        topic = "orders"
        key = b"key-bytes"
        value = b"value-bytes"

        await producer.send(topic, key, value)

        fake_producer.begin_transaction.assert_awaited_once()
        fake_producer.send_and_wait.assert_awaited_once_with(topic, key=key, value=value)
        fake_producer.commit_transaction.assert_awaited_once()
        fake_producer.abort_transaction.assert_not_awaited()

        await producer.stop()


@pytest.mark.asyncio
async def test_send_failure_aborts_transaction():
    """
    Если send_and_wait бросает исключение:
    1) abort_transaction вызывается,
    2) commit_transaction не вызывается.
    """
    fake_producer = AsyncMock()
    fake_producer.begin_transaction = AsyncMock()
    fake_producer.send_and_wait = AsyncMock(side_effect=RuntimeError("send failed"))
    fake_producer.commit_transaction = AsyncMock()
    fake_producer.abort_transaction = AsyncMock()
    fake_producer.start = AsyncMock()
    fake_producer.stop = AsyncMock()

    with patch(
        "src.infra.services.producer.AIOKafkaProducer",
        return_value=fake_producer
    ):
        producer = Producer(bootstrap_servers="dummy:9092", transactional_id="tran-id")
        await producer.start()

        with pytest.raises(RuntimeError):
            await producer.send("orders", b"key-fail", b"value-fail")

        fake_producer.begin_transaction.assert_awaited_once()
        fake_producer.send_and_wait.assert_awaited_once_with("orders", key=b"key-fail", value=b"value-fail")
        fake_producer.abort_transaction.assert_awaited_once()
        fake_producer.commit_transaction.assert_not_awaited()

        await producer.stop()
