import uuid
import datetime
from decimal import Decimal
from uuid import UUID as UUIDType

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.infra.postgres_repository import PostgresRepository
from src.infra.data.account import Account
from src.infra.data.inbox import PaymentInbox
from src.infra.data.outbox import PaymentOutbox
from src.infra.exceptions import DublicateAccountException, NoSuchAccountError


@pytest.mark.asyncio
async def test_create_account_and_duplicate(repository, session):
    user_id = uuid.uuid4()

    before = await session.execute(Account.__table__.select())
    assert before.all() == []

    account = await repository.create_account(user_id=user_id)
    assert isinstance(account, Account)
    assert isinstance(account.user_id, UUIDType)
    assert account.user_id == user_id
    assert account.balance == Decimal("0.00")

    rows = (await session.execute(Account.__table__.select())).mappings().all()
    assert len(rows) == 1
    row = rows[0]
    assert row["user_id"] == user_id
    assert row["balance"] == Decimal("0.00")

    with pytest.raises(DublicateAccountException):
        await repository.create_account(user_id=user_id)


@pytest.mark.asyncio
async def test_update_and_get_account_balance(repository, session):
    user_id = uuid.uuid4()
    dummy_balance = Decimal("10.00")

    with pytest.raises(NoSuchAccountError):
        await repository.update_balance(user_id, dummy_balance)
    with pytest.raises(NoSuchAccountError):
        await repository.get_account_balance(user_id)

    await repository.create_account(user_id=user_id)
    bal = await repository.get_account_balance(user_id)
    assert bal == {"user_id": user_id, "balance": Decimal("0.00")}

    new_bal = Decimal("123.45")
    updated_account = await repository.update_balance(user_id, new_bal)
    assert isinstance(updated_account, Account)
    assert updated_account.balance == new_bal

    bal2 = await repository.get_account_balance(user_id)
    assert bal2 == {"user_id": user_id, "balance": new_bal}

    fake_id = uuid.uuid4()
    with pytest.raises(NoSuchAccountError):
        await repository.update_balance(fake_id, Decimal("1.00"))
    with pytest.raises(NoSuchAccountError):
        await repository.get_account_balance(fake_id)


@pytest.mark.asyncio
async def test_insert_and_read_payment_inbox_and_update_processed_at(repository, session):
    assert await repository.get_payments_inbox() == []

    payload1 = {"order_id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()), "amount": "10.00"}
    payload2 = {"order_id": str(uuid.uuid4()), "user_id": str(uuid.uuid4()), "amount": "20.00"}
    await repository.insert_payment_inbox(payment_data=payload1)
    await repository.insert_payment_inbox(payment_data=payload2)

    entries = await repository.get_payments_inbox()
    assert len(entries) == 2
    for entry in entries:
        assert isinstance(entry, PaymentInbox)
        assert entry.processed_at is None
        assert isinstance(entry.payload, dict)

    first_id = entries[0].id
    await repository.update_processed_at(first_id)

    remaining = await repository.get_payments_inbox()
    assert len(remaining) == 1
    assert remaining[0].id != first_id

    row = (await session.execute(
        select(PaymentInbox).where(PaymentInbox.id == first_id)
    )).scalar_one()
    assert row.processed_at is not None


@pytest.mark.asyncio
async def test_get_account(repository):
    """ get_account должен возвращать Account, если аккаунт существует, и None, если нет. """
    user_id = uuid.uuid4()

    assert await repository.get_account(user_id) is None

    await repository.create_account(user_id=user_id)
    acc = await repository.get_account(user_id)
    assert isinstance(acc, Account)
    assert acc.user_id == user_id


@pytest.mark.asyncio
async def test_outbox_insert_and_read_and_update_status(repository, session):
    assert await repository.get_payments_outbox() == []

    payloads = [
        {"order_id": str(uuid.uuid4()), "status": "SUCCESS"},
        {"order_id": str(uuid.uuid4()), "status": "FAILED"},
        {"order_id": str(uuid.uuid4()), "status": "SUCCESS"},
    ]
    for pl in payloads:
        await repository.insert_payment_outbox(payment_data=pl, status=pl["status"])

    all_out = await repository.get_payments_outbox()
    assert len(all_out) == 3
    for entry in all_out:
        assert isinstance(entry, PaymentOutbox)
        assert entry.processed is False
        assert entry.status in ("SUCCESS", "FAILED")
        assert isinstance(entry.payload, dict)

    first_id = all_out[0].id
    await repository.update_outbox_payment_status(first_id)

    remaining = await repository.get_payments_outbox()
    assert len(remaining) == 2
    assert all(not e.processed for e in remaining)
    assert first_id not in [e.id for e in remaining]

    for e in remaining:
        await repository.update_outbox_payment_status(e.id)
    assert await repository.get_payments_outbox() == []