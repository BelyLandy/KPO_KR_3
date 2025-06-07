import uuid
from decimal import Decimal
from uuid import UUID as UUID_Type

import pytest

from src.infra.data.order import Order
from src.infra.data.outbox import OrderOutbox
from src.app.status import Status


@pytest.mark.asyncio
async def test_create_order_and_outbox(repository, session):
    """
    Проверяем, что create_order:
    - создает запись в таблице orders,
    - добавляет соответствующий outbox entry,
    - возвращает модель Order.
    """
    user_id = uuid.uuid4()
    amount = Decimal("42.00")
    description = "First test order"

    # До создания нет записей
    orders_before = await session.execute(Order.__table__.select())
    assert orders_before.mappings().all() == []
    outbox_before = await session.execute(OrderOutbox.__table__.select())
    assert outbox_before.mappings().all() == []

    # Создаем заказ
    new_order = await repository.create_order(
        user_id=user_id,
        amount=amount,
        description=description
    )

    # Проверяем возвращаемый объект
    assert isinstance(new_order, Order)
    assert isinstance(new_order.id, UUID_Type)
    assert new_order.user_id == user_id
    assert new_order.amount == amount
    assert new_order.description == description
    assert new_order.status == Status.NEW.value

    # В базе появился заказ
    result = await session.execute(Order.__table__.select())
    orders_after = result.mappings().all()
    assert len(orders_after) == 1
    saved = orders_after[0]
    assert saved["id"] == new_order.id
    assert saved["user_id"] == user_id
    assert saved["amount"] == amount
    assert saved["description"] == description
    assert saved["status"] == Status.NEW.value

    # В outbox появилась запись
    outbox_result = await session.execute(OrderOutbox.__table__.select())
    outbox_after = outbox_result.mappings().all()
    assert len(outbox_after) == 1
    entry = outbox_after[0]
    assert entry["event_type"] == "order_created"

    payload = entry["payload"]
    assert isinstance(payload, dict)
    assert payload["order_id"] == str(new_order.id)
    assert payload["user_id"] == str(user_id)
    assert payload["amount"] == str(amount)
    assert payload["description"] == description
    assert entry["processed"] is False


@pytest.mark.asyncio
async def test_get_orders(repository):
    """
    get_orders должно возвращать список ранее созданных заказов
    и без побочных эффектов для других пользователей.
    """
    user1 = uuid.uuid4()
    user2 = uuid.uuid4()

    # Нет заказов для user1
    empty = await repository.get_orders(user1)
    assert empty == []

    # Создаем заказы для двух пользователей
    o1 = await repository.create_order(user_id=user1, amount=Decimal("10.50"), description="u1-a")
    o2 = await repository.create_order(user_id=user1, amount=Decimal("11.50"), description="u1-b")
    await repository.create_order(user_id=user2, amount=Decimal("20.00"), description="u2-a")

    # Проверяем заказы для user1
    user1_orders = await repository.get_orders(user1)
    assert len(user1_orders) == 2
    ids = {o["id"] for o in user1_orders}
    assert ids == {o1.id, o2.id}
    for o in user1_orders:
        assert o["user_id"] == user1
        assert isinstance(o["amount"], Decimal)
        assert o["description"] in ["u1-a", "u1-b"]

    # Для случайного пользователя пусто
    assert await repository.get_orders(uuid.uuid4()) == []


@pytest.mark.asyncio
async def test_get_orders_outbox_and_update_outbox_status(repository):
    """
    Тестируем получение необработанных outbox-записей
    и их пометку как processed.
    """
    user_id = uuid.uuid4()

    # Изначально нет записей
    assert await repository.get_orders_outbox() == []

    # Создаем несколько заказов
    await repository.create_order(user_id=user_id, amount=Decimal("1"), description="A")
    await repository.create_order(user_id=user_id, amount=Decimal("2"), description="B")
    await repository.create_order(user_id=user_id, amount=Decimal("3"), description="C")

    # Проверяем все новые outbox-записи
    entries = await repository.get_orders_outbox()
    assert len(entries) == 3

    # Помечаем первую запись как processed
    first = entries[0]
    await repository.update_outbox_order_status(first.id)

    # Теперь должно остаться две необработанные
    remaining = await repository.get_orders_outbox()
    assert len(remaining) == 2
    assert all(not e.processed for e in remaining)
    assert first.id not in {e.id for e in remaining}

    # Отмечаем остальные записи
    for e in remaining:
        await repository.update_outbox_order_status(e.id)
    assert await repository.get_orders_outbox() == []


@pytest.mark.asyncio
async def test_get_order_status_and_update_order_status(repository):
    """
    Проверяем работу get_order_status и update_order_status:
    - для несуществующего заказа возвращается None,
    - после создания можно читать статус,
    - после обновления статус меняется,
    - обновление несуществующего заказа игнорируется.
    """
    fake_id = uuid.uuid4()
    assert await repository.get_order_status(fake_id) is None

    # Создаем заказ и проверяем статус
    user_id = uuid.uuid4()
    new_order = await repository.create_order(user_id=user_id, amount=Decimal("5.00"), description="X")
    status_before = await repository.get_order_status(new_order.id)
    assert status_before["order_id"] == new_order.id
    assert status_before["status"] == Status.NEW.value

    # Обновляем статус
    await repository.update_order_status(new_order.id, Status.FINISHED.value)
    status_after = await repository.get_order_status(new_order.id)
    assert status_after["status"] == Status.FINISHED.value

    # Обновление случайного ID не приводит к ошибке
    random_id = uuid.uuid4()
    await repository.update_order_status(random_id, Status.CANCELED.value)
    assert await repository.get_order_status(random_id) is None
