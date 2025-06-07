import datetime

from sqlalchemy import Column, String, JSON, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.infra.data.base import Base


class OrderOutbox(Base):
    """
    ORM-модель для таблицы «очереди событий» (outbox).
    """
    __tablename__ = "order_outbox"

    # Первичный ключ UUID записи в outbox
    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        comment="Уникальный идентификатор записи outbox",
    )

    # Тип события, например "order_created"
    event_type = Column(
        String,
        nullable=False,
        comment="Тип события для публикации",
    )

    # Полезная нагрузка события в формате JSON
    payload = Column(
        JSON,
        nullable=False,
        comment="Данные события",
    )

    # Время создания записи (UTC)
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        comment="Время создания записи",
    )

    # Флаг отправлено/обработано ли событие
    processed = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Признак обработки",
    )

    # Время, отложенное для отправки (если нужно отложить публикацию)
    send_at = Column(
        DateTime,
        nullable=True,
        comment="Время отложенной отправки",
    )
