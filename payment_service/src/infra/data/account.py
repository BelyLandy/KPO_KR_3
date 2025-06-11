from decimal import Decimal

from sqlalchemy import Column, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.infra.data.base import Base


class Account(Base):
    """ ORM-модель для таблицы аккаунтов. """
    __tablename__ = "accounts"

    user_id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        comment="UUID пользователя"
    )

    balance = Column(
        Numeric(precision=18, scale=2),
        nullable=False,
        comment="Баланс аккаунта"
    )
