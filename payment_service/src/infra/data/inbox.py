from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.infra.data.base import Base


class PaymentInbox(Base):
    """ ORM-модель для таблицы payment_inbox. """

    __tablename__ = "payment_inbox"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        comment="UUID записи входящего события"
    )

    event_type = Column(
        String,
        nullable=False,
        comment="Тип платежного события"
    )

    payload = Column(
        JSON,
        nullable=False,
        comment="Данные события в формате JSON"
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Время создания записи"
    )

    processed_at = Column(
        DateTime,
        nullable=True,
        comment="Время обработки записи"
    )
