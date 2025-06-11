import uuid
from typing import Optional, List, Dict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.data.order import Order as OrderModel
from src.infra.data.outbox import OrderOutbox as OutboxModel
from src.app.status import Status


class PostgresRepository:
    """ Репозиторий для работы с заказами и таблицей outbox в Postgres через SQLAlchemy AsyncSession. """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_order(
        self,
        user_id: UUID,
        amount: Decimal,
        description: Optional[str] = None
    ) -> OrderModel:
        """ Создает запись заказа и соответствующую запись в outbox. """
        order = OrderModel(
            id=uuid.uuid4(),
            user_id=user_id,
            amount=amount,
            description=description,
            status=Status.NEW.value
        )
        self._session.add(order)
        await self._session.flush()

        outbox = OutboxModel(
            id=uuid.uuid4(),
            event_type="order_created",
            payload={
                "order_id": str(order.id),
                "user_id": str(user_id),
                "amount": str(amount),
                "description": description,
            },
            processed=False
        )
        self._session.add(outbox)

        await self._session.commit()
        return order

    async def get_orders(self, user_id: UUID) -> List[Dict]:
        """ Возвращает все заказы указанного пользователя. """
        stmt = select(
            OrderModel.id,
            OrderModel.user_id,
            OrderModel.amount,
            OrderModel.description,
            OrderModel.status,
        ).where(OrderModel.user_id == user_id)

        result = await self._session.execute(stmt)
        return result.mappings().all()

    async def get_orders_outbox(self) -> List[OutboxModel]:
        """ Получает все необработанные записи из таблицы outbox, упорядоченные по времени создания. """
        stmt = (
            select(OutboxModel)
            .where(OutboxModel.processed.is_(False))
            .order_by(OutboxModel.created_at)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_order_status(self, order_id: UUID) -> Optional[Dict[str, str]]:
        """ Читает статус заказа по его UUID. """
        stmt = select(OrderModel).where(OrderModel.id == order_id)
        result = await self._session.execute(stmt)
        order = result.scalar_one_or_none()

        if order is None:
            return None

        return {"order_id": order.id, "status": order.status}

    async def update_outbox_order_status(self, outbox_id: UUID) -> None:
        """ Помечает запись outbox как обработанную. """
        stmt = (
            update(OutboxModel)
            .where(OutboxModel.id == outbox_id)
            .values(processed=True)
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def update_order_status(self, order_id: UUID, status: str) -> None:
        """ Обновляет поле status в записи заказа. """
        stmt = (
            update(OrderModel)
            .where(OrderModel.id == order_id)
            .values(status=status)
        )
        await self._session.execute(stmt)
        await self._session.commit()
