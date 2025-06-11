from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from src.infra.postgres_repository import PostgresRepository
from src.infra.exceptions import NegativeAmountError
from src.app.order import Order


class OrderService:
    """ Сервис для управления заказами: создание, получение списка и статуса. """

    def __init__(self, repository: PostgresRepository) -> None:
        self._repository = repository

    async def create_order(
            self,
            user_id: UUID,
            amount: Decimal,
            description: Optional[str] = None,
    ) -> Order:
        """ Создает новый заказ. """
        if amount <= 0:
            raise NegativeAmountError("Сумма заказа должна быть положительной")

        return await self._repository.create_order(
            user_id=user_id,
            amount=amount,
            description=description,
        )

    async def get_orders(self, user_id: UUID) -> List[Order]:
        """ Возвращает все заказы указанного пользователя. """
        return await self._repository.get_orders(user_id)

    async def get_order_status(self, order_id: UUID) -> Optional[Dict[str, Any]]:
        """ Возвращает текущий статус заказа в виде словаря с ключами. """
        return await self._repository.get_order_status(order_id)
