import uuid
from decimal import Decimal
from typing import Dict, List, Optional

import pytest
from unittest.mock import AsyncMock

from src.infra.services.order_service import OrderService
from src.infra.exceptions import NegativeAmountError
from src.app.status import Status


@pytest.mark.asyncio
async def test_create_order_success():
    """ Успешное создание заказа. """
    user_id = uuid.uuid4()
    amount = Decimal("50.00")
    description = "Test order"
    fake_order = {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "amount": amount,
        "description": description,
        "status": Status.NEW.value
    }

    mock_repo = AsyncMock()
    mock_repo.create_order.return_value = fake_order

    service = OrderService(repository=mock_repo)
    result = await service.create_order(
        user_id=user_id,
        amount=amount,
        description=description
    )

    assert result is fake_order
    mock_repo.create_order.assert_awaited_once_with(
        user_id=user_id,
        amount=amount,
        description=description
    )


@pytest.mark.asyncio
async def test_create_order_negative_amount_raises():
    """
    При отрицательной или нулевой сумме бросается NegativeAmountError,
    а репозиторий не вызывается.
    """
    mock_repo = AsyncMock()
    service = OrderService(repository=mock_repo)

    with pytest.raises(NegativeAmountError):
        await service.create_order(
            user_id=uuid.uuid4(),
            amount=Decimal("-10.00"),
            description="Invalid"
        )

    mock_repo.create_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_orders_delegates_to_repository():
    """
    get_orders должно просто делегировать вызов в репозиторий
    и возвращать полученный список заказов.
    """
    user_id = uuid.uuid4()
    fake_orders: List[Dict] = [
        {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "amount": Decimal("1.00"),
            "description": "A",
            "status": Status.NEW.value
        },
        {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "amount": Decimal("2.00"),
            "description": "B",
            "status": Status.NEW.value
        }
    ]

    mock_repo = AsyncMock()
    mock_repo.get_orders.return_value = fake_orders

    service = OrderService(repository=mock_repo)
    result = await service.get_orders(user_id=user_id)

    assert result is fake_orders
    mock_repo.get_orders.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_get_order_status_delegates_to_repository():
    """
    get_order_status должно делегировать в репозиторий
    и возвращать статус заказа или None.
    """
    order_id = uuid.uuid4()
    fake_status: Optional[Dict] = {
        "order_id": order_id,
        "status": Status.NEW.value
    }

    mock_repo = AsyncMock()
    mock_repo.get_order_status.return_value = fake_status

    service = OrderService(repository=mock_repo)
    result = await service.get_order_status(order_id=order_id)

    assert result is fake_status
    mock_repo.get_order_status.assert_awaited_once_with(order_id)
