import uuid
from uuid import UUID as UUIDType
from decimal import Decimal
from typing import List, Optional, Dict
import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.exceptions import (
    DublicateAccountException,
    NegativeAmountError,
    NoSuchAccountError,
)
from src.infra.data.account import Account
from src.infra.data.inbox import PaymentInbox
from src.infra.data.outbox import PaymentOutbox


class PostgresRepository:
    """
    Репозиторий для работы с аккаунтами и очередями платежей (inbox/outbox) в PostgreSQL.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        :param session: Асинхронная сессия SQLAlchemy
        """
        self._session = session

    async def create_account(self, user_id: UUIDType) -> Account:
        """
        Создает новый аккаунт с нулевым балансом.
        :raises DublicateAccountException: если аккаунт уже существует.
        """
        account = Account(user_id=user_id, balance=Decimal("0.00"))
        try:
            self._session.add(account)
            await self._session.commit()
        except IntegrityError:
            raise DublicateAccountException()
        return account

    async def update_balance(self, user_id: UUIDType, new_balance: Decimal) -> Account:
        """
        Обновляет баланс существующего аккаунта.
        :raises NoSuchAccountError: если аккаунт не найден.
        """
        stmt = select(Account).where(Account.user_id == user_id)
        result = await self._session.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            raise NoSuchAccountError()

        account.balance = new_balance
        await self._session.commit()
        return account

    async def get_account_balance(self, user_id: UUIDType) -> Dict[str, Decimal]:
        """
        Возвращает баланс аккаунта по UUID.
        :raises NoSuchAccountError: если аккаунт не найден.
        """
        stmt = select(Account).where(Account.user_id == user_id)
        result = await self._session.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            raise NoSuchAccountError()

        return {"user_id": account.user_id, "balance": account.balance}

    async def insert_payment_inbox(self, payment_data: Dict) -> None:
        """
        Помещает новое платежное событие в очередь inbox.
        """
        entry = PaymentInbox(
            id=uuid.uuid4(),
            event_type="payment_new",
            payload=payment_data,
        )
        self._session.add(entry)
        await self._session.commit()

    async def get_payments_inbox(self) -> List[PaymentInbox]:
        """
        Получает все необработанные записи из payment_inbox.
        """
        stmt = select(PaymentInbox).where(PaymentInbox.processed_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_account(self, user_id: UUIDType) -> Optional[Account]:
        """
        Проверяет наличие аккаунта; возвращает объект или None.
        """
        stmt = select(Account).where(Account.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_processed_at(self, record_id: UUIDType) -> None:
        """
        Отмечает запись в inbox как обработанную.
        """
        stmt = (
            update(PaymentInbox)
            .where(PaymentInbox.id == record_id)
            .values(processed_at=datetime.datetime.utcnow())
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def insert_payment_outbox(self, payment_data: Dict, status: str) -> None:
        """
        Помещает событие обработки платежа в очередь outbox.
        """
        entry = PaymentOutbox(
            id=uuid.uuid4(),
            event_type="payment_processed",
            payload=payment_data,
            status=status,
            processed=False,
        )
        self._session.add(entry)
        await self._session.commit()

    async def get_payments_outbox(self) -> List[PaymentOutbox]:
        """
        Получает все необработанные записи из payment_outbox,
        упорядоченные по времени создания.
        """
        stmt = (
            select(PaymentOutbox)
            .where(PaymentOutbox.processed.is_(False))
            .order_by(PaymentOutbox.created_at)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_outbox_payment_status(self, outbox_id: UUIDType) -> None:
        """
        Отмечает запись в outbox как обработанную (processed=True).
        """
        stmt = (
            update(PaymentOutbox)
            .where(PaymentOutbox.id == outbox_id)
            .values(processed=True)
        )
        await self._session.execute(stmt)
        await self._session.commit()
