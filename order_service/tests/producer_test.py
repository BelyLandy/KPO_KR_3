import uuid
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.infra.services.producer import Producer


@pytest.mark.asyncio
async def test_start_and_stop_invokes_kafka_methods():
    """
    Убеждаемся, что Producer.start/stop вызывают соответствующие методы AIOKafkaProducer.
    """
    fake_kafka = AsyncMock()
    with patch(
        "src.infra.services.producer.AIOKafkaProducer",
        return_value=fake_kafka
    ):
        producer = Producer(
            bootstrap_servers="dummy:9092",
            transactional_id="tx1"
        )

        # act
        await producer.start()
        await producer.stop()

        # assert
        fake_kafka.start.assert_awaited_once()
        fake_kafka.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_commits_transaction_on_success():
    """
    Проверяем, что при успешной отправке:
    - сначала вызывается begin_transaction,
    - затем send_and_wait,
    - и в конце commit_transaction,
    - abort_transaction не вызывается.
    """
    fake_kafka = AsyncMock()
    fake_kafka.send_and_wait = AsyncMock()
    # Список для отслеживания порядка вызовов
    calls = []

    # мокаем begin/commit
    async def fake_begin():
        calls.append("begin")

    async def fake_commit():
        calls.append("commit")

    fake_kafka.begin_transaction.side_effect = fake_begin
    fake_kafka.commit_transaction.side_effect = fake_commit
    fake_kafka.abort_transaction = AsyncMock()

    with patch(
        "src.infra.services.producer.AIOKafkaProducer",
        return_value=fake_kafka
    ):
        producer = Producer(
            bootstrap_servers="dummy:9092",
            transactional_id="tx2"
        )

        # act
        await producer.send(
            topic="t1",
            key=b"k1",
            value=b"v1"
        )

        # assert
        assert calls == ["begin", "commit"]
        fake_kafka.send_and_wait.assert_awaited_once_with(
            "t1", key=b"k1", value=b"v1"
        )
        fake_kafka.abort_transaction.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_aborts_transaction_on_error():
    """
    Если send_and_wait бросает исключение:
    - begin_transaction вызывается,
    - затем abort_transaction,
    - commit_transaction не вызывается.
    """
    fake_kafka = AsyncMock()

    async def fake_begin():
        pass

    async def fake_send(topic, key, value):
        raise RuntimeError("send failed")

    fake_kafka.begin_transaction.side_effect = fake_begin
    fake_kafka.send_and_wait.side_effect  = fake_send
    fake_kafka.commit_transaction = AsyncMock()
    fake_kafka.abort_transaction  = AsyncMock()

    with patch(
        "src.infra.services.producer.AIOKafkaProducer",
        return_value=fake_kafka
    ):
        producer = Producer(
            bootstrap_servers="dummy:9092",
            transactional_id="tx3"
        )

        # act/assert
        with pytest.raises(RuntimeError):
            await producer.send(
                topic="t2",
                key=b"k2",
                value=b"v2"
            )

        fake_kafka.begin_transaction.assert_awaited_once()
        fake_kafka.abort_transaction.assert_awaited_once()
        fake_kafka.commit_transaction.assert_not_awaited()
