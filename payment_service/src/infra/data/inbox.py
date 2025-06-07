from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.infra.data.base import Base


class PaymentInbox(Base):
    """
    ORM-модель для таблицы payment_inbox:
    хранит входящие запросы платежей.
    """

    __tablename__ = "payment_inbox"

    # Уникальный идентификатор записи
    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        comment="UUID записи входящего события"
    )

    # Тип события, например "PaymentRequest" или "PaymentResponse"
    event_type = Column(
        String,
        nullable=False,
        comment="Тип платежного события"
    )

    # JSON-полезная нагрузка события
    payload = Column(
        JSON,
        nullable=False,
        comment="Данные события в формате JSON"
    )

    # Дата и время создания записи (UTC)
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Время создания записи"
    )

    # Дата и время обработки (пометка о завершении)
    processed_at = Column(
        DateTime,
        nullable=True,
        comment="Время обработки записи"
    )
