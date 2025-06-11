import asyncio
import json
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, call

from src.infra.services.outbox_publisher import OutboxPublisher


@pytest.mark.asyncio
async def test_get_orders_sends_and_updates():
    """
    Получение необработанных записей из outbox.
    Отправку payload в Kafka через broker.send.
    Обновление статуса каждой записи через repository.update_outbox_order_status.
    """
    payload1 = {"order_id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()), "amount": "10"}
    payload2 = {"order_id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()), "amount": "20"}

    entry1 = MagicMock(id=uuid.uuid4(), payload=payload1)
    entry2 = MagicMock(id=uuid.uuid4(), payload=payload2)

    mock_repo = AsyncMock()
    mock_repo.get_orders_outbox.return_value = [entry1, entry2]
    mock_repo.update_outbox_order_status = AsyncMock()

    mock_broker = AsyncMock()
    mock_broker.send = AsyncMock()
    mock_broker.start = AsyncMock()
    mock_broker.stop = AsyncMock()

    publisher = OutboxPublisher(repository=mock_repo, broker=mock_broker)

    await publisher._publish_pending()

    mock_repo.get_orders_outbox.assert_awaited_once()

    expected_sends = [
        call(topic="order", key=None, value=json.dumps(payload1).encode("utf-8")),
        call(topic="order", key=None, value=json.dumps(payload2).encode("utf-8")),
    ]
    mock_broker.send.assert_has_awaits(expected_sends, any_order=False)

    expected_updates = [call(entry1.id), call(entry2.id)]
    mock_repo.update_outbox_order_status.assert_has_awaits(expected_updates, any_order=False)


@pytest.mark.asyncio
async def test_run_starts_and_stops_broker_and_calls_get_orders_periodically(monkeypatch):
    """ Проверяет метод run. """
    mock_repo = AsyncMock()
    mock_broker = AsyncMock()
    mock_broker.start = AsyncMock()
    mock_broker.stop = AsyncMock()
    mock_broker.send = AsyncMock()

    publisher = OutboxPublisher(repository=mock_repo, broker=mock_broker)
    publisher._publish_pending = AsyncMock()

    async def runner():
        await publisher.run(interval=0)

    task = asyncio.create_task(runner())
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    mock_broker.start.assert_awaited_once()
    assert publisher._publish_pending.await_count >= 1
    mock_broker.stop.assert_awaited_once()