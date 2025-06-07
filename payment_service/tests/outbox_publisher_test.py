import asyncio
import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.infra.services.outbox_publisher import OutboxPublisher
from src.infra.postgres_repository import PostgresRepository
from src.infra.services.producer import Producer


@pytest.mark.asyncio
async def test_publish_pending_success():
    """
    Успешная отправка:
    - get_payments_outbox возвращает записи,
    - broker.send вызывается с payload + status,
    - update_outbox_payment_status вызывается для каждой записи.
    """
    # Подготовка двух записей outbox
    entry1 = MagicMock(id="id1", payload={"a": 1}, status="pending")
    entry2 = MagicMock(id="id2", payload={"b": 2}, status="done")

    repo = AsyncMock(spec=PostgresRepository)
    repo.get_payments_outbox.return_value = [entry1, entry2]
    repo.update_outbox_payment_status = AsyncMock()

    broker = AsyncMock(spec=Producer)
    broker.send = AsyncMock()

    publisher = OutboxPublisher(repository=repo, broker=broker)
    await publisher._publish_pending()

    # Проверяем вызов получения из репозитория
    repo.get_payments_outbox.assert_awaited_once()

    # Проверяем вызов send с объединённым payload+status
    expected1 = json.dumps({**entry1.payload, "status": entry1.status}).encode("utf-8")
    expected2 = json.dumps({**entry2.payload, "status": entry2.status}).encode("utf-8")
    broker.send.assert_any_await(topic="payments", key=None, value=expected1)
    broker.send.assert_any_await(topic="payments", key=None, value=expected2)
    assert broker.send.await_count == 2

    # Проверяем пометку записей как обработанных
    repo.update_outbox_payment_status.assert_any_await(entry1.id)
    repo.update_outbox_payment_status.assert_any_await(entry2.id)
    assert repo.update_outbox_payment_status.await_count == 2


@pytest.mark.asyncio
async def test_publish_pending_send_failure():
    """
    Если broker.send бросает, то для этой записи update_outbox_payment_status не вызывается,
    но остальные записи обрабатываются.
    """
    entry1 = MagicMock(id="id1", payload={"a": 1}, status="pending")
    entry2 = MagicMock(id="id2", payload={"b": 2}, status="done")

    repo = AsyncMock(spec=PostgresRepository)
    repo.get_payments_outbox.return_value = [entry1, entry2]
    repo.update_outbox_payment_status = AsyncMock()

    # broker.send для первой записи бросает, для второй — нет
    async def send_side_effect(topic, key, value):
        if value == json.dumps({**entry1.payload, "status": entry1.status}).encode("utf-8"):
            raise RuntimeError("fail")
    broker = AsyncMock(spec=Producer)
    broker.send = AsyncMock(side_effect=send_side_effect)

    publisher = OutboxPublisher(repository=repo, broker=broker)
    await publisher._publish_pending()

    # Обе попытки отправки
    expected1 = json.dumps({**entry1.payload, "status": entry1.status}).encode("utf-8")
    expected2 = json.dumps({**entry2.payload, "status": entry2.status}).encode("utf-8")
    broker.send.assert_any_await(topic="payments", key=None, value=expected1)
    broker.send.assert_any_await(topic="payments", key=None, value=expected2)
    assert broker.send.await_count == 2

    # update_outbox_payment_status вызывается только для второй (успешной) записи
    repo.update_outbox_payment_status.assert_awaited_once_with(entry2.id)


@pytest.mark.asyncio
async def test_run_starts_and_stops_and_publishes_periodically():
    """
    run():
    - вызывает broker.start(),
    - затем _publish_pending(),
    - затем broker.stop() при выходе.
    """
    repo = AsyncMock(spec=PostgresRepository)
    broker = AsyncMock(spec=Producer)
    broker.start = AsyncMock()
    broker.stop = AsyncMock()

    publisher = OutboxPublisher(repository=repo, broker=broker)
    # После одного вызова _publish_pending бросаем StopAsyncIteration, чтобы выйти из цикла
    publisher._publish_pending = AsyncMock(side_effect=[None, StopAsyncIteration])

    with pytest.raises(StopAsyncIteration):
        await publisher.run(interval=0)

    # Проверяем порядок вызовов
    broker.start.assert_awaited_once()
    publisher._publish_pending.assert_awaited()  # хотя бы один раз
    broker.stop.assert_awaited_once()
