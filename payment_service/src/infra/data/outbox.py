from datetime import datetime
from sqlalchemy import Column, String, JSON, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.infra.data.base import Base


class PaymentOutbox(Base):
    """
    ORM-модель для таблицы payment_outbox:
    хранит события для последующей отправки в Kafka.
    """
    __tablename__ = "payment_outbox"

    # UUID записи outbox
    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        comment="Уникальный идентификатор записи"
    )

    # Тип события, например "PaymentRequest"
    event_type = Column(
        String,
        nullable=False,
        comment="Тип события для публикации"
    )

    # Полезная нагрузка события в формате JSON
    payload = Column(
        JSON,
        nullable=False,
        comment="Данные события"
    )

    # Статус события (pending/success/failed и т.п.)
    status = Column(
        String,
        nullable=False,
        comment="Текущий статус события"
    )

    # Время создания записи (UTC)
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Время создания записи"
    )

    # Флаг обработки записи
    processed = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Признак отправки/обработки"
    )

    # Время отложенной отправки (если необходимо)
    send_at = Column(
        DateTime,
        nullable=True,
        comment="Запланированное время отправки"
    )
