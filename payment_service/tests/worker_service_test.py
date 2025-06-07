import asyncio
import json
from decimal import Decimal
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.infra.services.worker_service import Worker


@pytest.mark.asyncio
async def test_process_inbox_no_account_inserts_fail_and_marks_processed():
    """
    Если аккаунт не найден:
    - insert_payment_outbox вызывается с status="canceled",
    - update_processed_at вызывается с id записи,
    - update_balance не вызывается.
    """
    order_id = uuid4()
    payload = {"order_id": str(order_id), "user_id": str(uuid4()), "amount": "100.00"}
    entry = MagicMock(id=order_id, payload=json.dumps(payload))

    repo = AsyncMock()
    repo.get_payments_inbox.return_value = [entry]
    repo.get_account.return_value = None
    repo.insert_payment_outbox = AsyncMock()
    repo.update_processed_at = AsyncMock()
    repo.update_balance = AsyncMock()

    worker = Worker(repository=repo)
    await worker._process_inbox()

    repo.get_payments_inbox.assert_awaited_once()
    repo.get_account.assert_awaited_once_with(payload["user_id"])
    repo.insert_payment_outbox.assert_awaited_once_with(payload, status="canceled")
    repo.update_processed_at.assert_awaited_once_with(order_id)
    repo.update_balance.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_inbox_insufficient_balance_inserts_fail_and_marks_processed():
    """
    Если баланс аккаунта меньше суммы:
    - insert_payment_outbox вызывается с status="cancelled",
    - update_processed_at вызывается,
    - update_balance не вызывается.
    """
    order_id = uuid4()
    user_id = uuid4()
    payload = {"order_id": str(order_id), "user_id": str(user_id), "amount": "200.00"}
    entry = MagicMock(id=order_id, payload=json.dumps(payload))

    account = MagicMock(user_id=user_id, balance=Decimal("50.00"))

    repo = AsyncMock()
    repo.get_payments_inbox.return_value = [entry]
    repo.get_account.return_value = account
    repo.insert_payment_outbox = AsyncMock()
    repo.update_processed_at = AsyncMock()
    repo.update_balance = AsyncMock()

    worker = Worker(repository=repo)
    await worker._process_inbox()

    repo.get_account.assert_awaited_once_with(payload["user_id"])
    repo.insert_payment_outbox.assert_awaited_once_with(payload, status="canceled")
    repo.update_processed_at.assert_awaited_once_with(order_id)
    repo.update_balance.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_inbox_sufficient_balance_updates_and_inserts_success():
    """
    Если баланс аккаунта >= суммы:
    - update_balance вызывается с новым балансом (используя строковый user_id),
    - update_processed_at вызывается,
    - insert_payment_outbox вызывается с status="finished",.
    """
    order_id = uuid4()
    user_uuid = uuid4()
    payload = {"order_id": str(order_id), "user_id": str(user_uuid), "amount": "30.00"}
    entry = MagicMock(id=order_id, payload=json.dumps(payload))

    initial_balance = Decimal("100.00")
    account = MagicMock(user_id=user_uuid, balance=initial_balance)

    repo = AsyncMock()
    repo.get_payments_inbox.return_value = [entry]
    repo.get_account.return_value = account
    repo.insert_payment_outbox = AsyncMock()
    repo.update_processed_at = AsyncMock()
    repo.update_balance = AsyncMock()

    worker = Worker(repository=repo)
    await worker._process_inbox()

    new_balance = initial_balance - Decimal(payload["amount"])
    # Проверяем, что update_balance вызван со строковым user_id из payload
    repo.update_balance.assert_awaited_once_with(payload["user_id"], new_balance)
    repo.update_processed_at.assert_awaited_once_with(order_id)
    repo.insert_payment_outbox.assert_awaited_once_with(payload, status="finished")


@pytest.mark.asyncio
async def test_run_loops_and_processes_until_exception(monkeypatch):
    """
    run() должен:
    - вызывать asyncio.sleep(interval) перед каждым _process_inbox,
    - вызывать _process_inbox,
    - повторять до тех пор, пока _process_inbox не бросит StopAsyncIteration,
    - в итоге sleep вызывается дважды (до первого и второго вызова _process_inbox).
    """
    repo = AsyncMock()
    worker = Worker(repository=repo)

    # _process_inbox сначала отрабатывает, затем выбрасывает StopAsyncIteration
    worker._process_inbox = AsyncMock(side_effect=[None, StopAsyncIteration])

    sleep_calls = []

    async def fake_sleep(interval):
        sleep_calls.append(interval)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with pytest.raises(StopAsyncIteration):
        await worker.run(interval=0.1)

    # Ожидаем два сна: перед первым и перед вторым вызовом _process_inbox
    assert sleep_calls == [0.1, 0.1]
    assert worker._process_inbox.await_count == 2
