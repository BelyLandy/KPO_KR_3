from typing import Optional, Dict
from uuid import UUID
from decimal import Decimal

from src.infra.postgres_repository import PostgresRepository
from src.app.account import Account
from src.infra.exceptions import DublicateAccountException, NegativeAmountError


class PaymentService:
    """ Сервис для создания аккаунтов и управления балансом пользователей. """

    def __init__(self, repository: PostgresRepository) -> None:
        self._repo = repository

    async def create_account(self, user_id: UUID) -> Account:
        """ Создает аккаунт для пользователя или возвращает уже существующий. """
        return await self._repo.create_account(user_id)

    async def update_account_balance(self, user_id: UUID, amount: Decimal) -> None:
        """ Пополняет баланс аккаунта на указанную сумму. """
        if amount <= 0:
            raise NegativeAmountError("Amount must be positive.")

        current = await self._repo.get_account_balance(user_id)
        new_balance = current["balance"] + amount
        await self._repo.update_balance(user_id, new_balance)

    async def get_account_balance(self, user_id: UUID) -> Optional[Dict]:
        """ Возвращает текущий баланс указанного аккаунта. """
        return await self._repo.get_account_balance(user_id)
