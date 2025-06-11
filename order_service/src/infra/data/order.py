from decimal import Decimal
from sqlalchemy import Column, String, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from src.infra.data.base import Base


class Order(Base):
    """ ORM-модель для таблицы заказов. """
    __tablename__ = "orders"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        comment="Уникальный UUID заказа",
    )

    user_id = Column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="UUID пользователя",
    )

    amount = Column(
        Numeric(precision=10),
        nullable=False,
        comment="Сумма заказа",
    )

    description = Column(
        String,
        nullable=True,
        comment="Описание заказа",
    )

    status = Column(
        String,
        nullable=False,
        comment="Строковое представление статуса заказа",
    )
