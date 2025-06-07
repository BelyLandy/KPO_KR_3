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
    """
    1. В начале таблица accounts пуста.
    2. После create_account появляется одна запись.
    3. Повторный вызов create_account для того же user_id должен бросить DublicateAccountException.
    """
    user_id = uuid.uuid4()

    # Шаг 1: проверяем, что до создания нет записей
    before = await session.execute(Account.__table__.select())
    assert before.all() == []

    # Шаг 2: создаём аккаунт и проверяем его поля
    account = await repository.create_account(user_id=user_id)
    assert isinstance(account, Account)
    assert isinstance(account.user_id, UUIDType)
    assert account.user_id == user_id
    assert account.balance == Decimal("0.00")

    # Шаг 2.1: проверяем вставку в БД
    rows = (await session.execute(Account.__table__.select())).mappings().all()
    assert len(rows) == 1
    row = rows[0]
    assert row["user_id"] == user_id
    assert row["balance"] == Decimal("0.00")

    # Шаг 3: повторный create_account должен бросить исключение
    with pytest.raises(DublicateAccountException):
        await repository.create_account(user_id=user_id)


@pytest.mark.asyncio
async def test_update_and_get_account_balance(repository, session):
    """
    1. При отсутствии аккаунта update_balance и get_account_balance бросают NoSuchAccountError.
    2. После создания аккаунта get_account_balance возвращает начальный баланс.
    3. update_balance обновляет баланс, который затем возвращается get_account_balance.
    4. Для случайного user_id операции снова бросают NoSuchAccountError.
    """
    user_id = uuid.uuid4()
    dummy_balance = Decimal("10.00")

    # 1. Операции на несуществующем аккаунте
    with pytest.raises(NoSuchAccountError):
        await repository.update_balance(user_id, dummy_balance)
    with pytest.raises(NoSuchAccountError):
        await repository.get_account_balance(user_id)

    # 2. Создаём аккаунт и читаем баланс
    await repository.create_account(user_id=user_id)
    bal = await repository.get_account_balance(user_id)
    assert bal == {"user_id": user_id, "balance": Decimal("0.00")}

    # 3. Обновляем баланс и проверяем
    new_bal = Decimal("123.45")
    updated_account = await repository.update_balance(user_id, new_bal)
    assert isinstance(updated_account, Account)
    assert updated_account.balance == new_bal

    bal2 = await repository.get_account_balance(user_id)
    assert bal2 == {"user_id": user_id, "balance": new_bal}

    # 4. Проверяем NoSuchAccountError для другого UUID
    fake_id = uuid.uuid4()
    with pytest.raises(NoSuchAccountError):
        await repository.update_balance(fake_id, Decimal("1.00"))
    with pytest.raises(NoSuchAccountError):
        await repository.get_account_balance(fake_id)


@pytest.mark.asyncio
async def test_insert_and_read_payment_inbox_and_update_processed_at(repository, session):
    """
    1. В начале inbox пуст.
    2. После двух insert_payment_inbox появляются две записи с processed_at=None.
    3. update_processed_at помечает первую запись, и она больше не возвращается get_payments_inbox.
    """
    # 1. Проверяем пустой inbox
    assert await repository.get_payments_inbox() == []

    # 2. Добавляем две записи
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

    # 3. Помечаем первый как обработанный
    first_id = entries[0].id
    await repository.update_processed_at(first_id)

    remaining = await repository.get_payments_inbox()
    assert len(remaining) == 1
    assert remaining[0].id != first_id

    # Проверяем, что в БД processed_at установлен
    row = (await session.execute(
        select(PaymentInbox).where(PaymentInbox.id == first_id)
    )).scalar_one()
    assert row.processed_at is not None


@pytest.mark.asyncio
async def test_get_account(repository):
    """
    get_account должен возвращать Account, если аккаунт существует,
    и None, если нет.
    """
    user_id = uuid.uuid4()

    # Сначала None
    assert await repository.get_account(user_id) is None

    # После создания возвращает объект Account
    await repository.create_account(user_id=user_id)
    acc = await repository.get_account(user_id)
    assert isinstance(acc, Account)
    assert acc.user_id == user_id


@pytest.mark.asyncio
async def test_outbox_insert_and_read_and_update_status(repository, session):
    """
    1. В начале outbox пуст.
    2. insert_payment_outbox создаёт записи с processed=False.
    3. get_payments_outbox возвращает только необработанные.
    4. update_outbox_payment_status помечает запись processed=True и исключает её из выдачи.
    """
    # 1. Пустой outbox
    assert await repository.get_payments_outbox() == []

    # 2. Добавляем три записи
    payloads = [
        {"order_id": str(uuid.uuid4()), "status": "SUCCESS"},
        {"order_id": str(uuid.uuid4()), "status": "FAILED"},
        {"order_id": str(uuid.uuid4()), "status": "SUCCESS"},
    ]
    for pl in payloads:
        await repository.insert_payment_outbox(payment_data=pl, status=pl["status"])

    # 3. Читаем все
    all_out = await repository.get_payments_outbox()
    assert len(all_out) == 3
    for entry in all_out:
        assert isinstance(entry, PaymentOutbox)
        assert entry.processed is False
        assert entry.status in ("SUCCESS", "FAILED")
        assert isinstance(entry.payload, dict)

    # 4. Помечаем первые две как обработанные и проверяем
    first_id = all_out[0].id
    await repository.update_outbox_payment_status(first_id)

    remaining = await repository.get_payments_outbox()
    assert len(remaining) == 2
    assert all(not e.processed for e in remaining)
    assert first_id not in [e.id for e in remaining]

    # Обрабатываем оставшиеся
    for e in remaining:
        await repository.update_outbox_payment_status(e.id)
    assert await repository.get_payments_outbox() == []
