from datetime import datetime
from sqlalchemy import Column, String, JSON, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.infra.data.base import Base


class PaymentOutbox(Base):
    """ ORM-модель для таблицы payment_outbox. """
    __tablename__ = "payment_outbox"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        comment="Уникальный идентификатор записи"
    )

    event_type = Column(
        String,
        nullable=False,
        comment="Тип события для публикации"
    )

    payload = Column(
        JSON,
        nullable=False,
        comment="Данные события"
    )

    status = Column(
        String,
        nullable=False,
        comment="Текущий статус события"
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Время создания записи"
    )

    processed = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Признак отправки/обработки"
    )

    send_at = Column(
        DateTime,
        nullable=True,
        comment="Запланированное время отправки"
    )
