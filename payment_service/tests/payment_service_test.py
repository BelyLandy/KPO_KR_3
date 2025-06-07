import uuid
from decimal import Decimal
from typing import Dict, Optional

import pytest
from unittest.mock import AsyncMock

from src.infra.postgres_repository import PostgresRepository
from src.infra.exceptions import DublicateAccountException, NegativeAmountError
from src.app.account import Account
from src.infra.services.payment_service import PaymentService


@pytest.mark.asyncio
async def test_create_account_delegates_and_returns_account():
    """
    PaymentService.create_account должен вызвать репозиторий
    и вернуть объект Account.
    """
    # Arrange
    repo = AsyncMock(spec=PostgresRepository)
    fake_account = Account(user_id=uuid.uuid4(), balance=Decimal("0.00"))
    repo.create_account.return_value = fake_account
    service = PaymentService(repository=repo)
    user_id = uuid.uuid4()

    # Act
    result = await service.create_account(user_id)

    # Assert
    repo.create_account.assert_awaited_once_with(user_id)
    assert result is fake_account


@pytest.mark.asyncio
async def test_create_account_duplicate_raises_exception():
    """
    Если репозиторий бросает DublicateAccountException,
    сервис тоже должен её пробросить.
    """
    repo = AsyncMock(spec=PostgresRepository)
    repo.create_account.side_effect = DublicateAccountException("Exists")
    service = PaymentService(repository=repo)
    user_id = uuid.uuid4()

    with pytest.raises(DublicateAccountException) as exc_info:
        await service.create_account(user_id)

    assert "Exists" in str(exc_info.value)
    repo.create_account.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_update_account_balance_positive_amount():
    """
    При положительном amount сервис:
    1) вызывает get_account_balance,
    2) рассчитывает новый баланс,
    3) вызывает update_balance с новым балансом.
    """
    repo = AsyncMock(spec=PostgresRepository)
    initial = Decimal("100.00")
    repo.get_account_balance.return_value = {"user_id": uuid.uuid4(), "balance": initial}
    repo.update_balance.return_value = None

    service = PaymentService(repository=repo)
    user_id = uuid.uuid4()
    increment = Decimal("25.50")

    await service.update_account_balance(user_id, increment)

    repo.get_account_balance.assert_awaited_once_with(user_id)
    repo.update_balance.assert_awaited_once_with(user_id, initial + increment)


@pytest.mark.asyncio
async def test_update_account_balance_non_positive_amount_raises():
    """
    При amount <= 0 сервис должен бросить NegativeAmountError
    и не вызывать репозиторий.
    """
    repo = AsyncMock(spec=PostgresRepository)
    service = PaymentService(repository=repo)
    user_id = uuid.uuid4()

    for bad_amount in [Decimal("0.00"), Decimal("-5.00")]:
        with pytest.raises(NegativeAmountError):
            await service.update_account_balance(user_id, bad_amount)

    # Никаких вызовов в репозиторий не должно быть
    repo.get_account_balance.assert_not_awaited()
    repo.update_balance.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_account_balance_delegates_and_returns():
    """
    PaymentService.get_account_balance должен вызывать репозиторий
    и возвращать его результат.
    """
    repo = AsyncMock(spec=PostgresRepository)
    expected: Optional[Dict] = {"user_id": uuid.uuid4(), "balance": Decimal("42.42")}
    repo.get_account_balance.return_value = expected

    service = PaymentService(repository=repo)
    user_id = uuid.uuid4()

    result = await service.get_account_balance(user_id)

    repo.get_account_balance.assert_awaited_once_with(user_id)
    assert result == expected
