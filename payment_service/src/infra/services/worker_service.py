import asyncio
import json
from decimal import Decimal

from src.infra.postgres_repository import PostgresRepository


class Worker:
    """ Фоновый воркер для чтения платежных запросов из inbox, проверки баланса и записи результатов в outbox. """

    def __init__(self, repository: PostgresRepository) -> None:
        self._repo = repository

    async def _process_inbox(self) -> None:
        """ Обрабатывает незавершённые записи из payment_inbox. """
        entries = await self._repo.get_payments_inbox()
        for entry in entries:
            data = json.loads(entry.payload)
            user_id = data["user_id"]
            amount = Decimal(data["amount"])

            account = await self._repo.get_account(user_id)
            if account is None:
                await self._repo.insert_payment_outbox(data, status="canceled")
                await self._repo.update_processed_at(entry.id)
                return

            if account.balance < amount:
                await self._repo.insert_payment_outbox(data, status="canceled")
                await self._repo.update_processed_at(entry.id)
                return

            new_balance = account.balance - amount
            await self._repo.update_balance(user_id, new_balance)
            await self._repo.update_processed_at(entry.id)
            await self._repo.insert_payment_outbox(data, status="finished")

    async def run(self, interval: int = 2) -> None:
        """ Запускает бесконечный цикл обработки inbox каждые interval секунд. """
        while True:
            await asyncio.sleep(interval)
            await self._process_inbox()
