from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide
from pydantic import BaseModel

from src.dependencies import Container
from src.infra.services.order_service import OrderService
from src.infra.exceptions import NegativeAmountError
from src.app.order import Order


class OrderCreateRequest(BaseModel):
    """
    Тело запроса для создания нового заказа.
    """
    user_id: UUID
    amount: Decimal
    description: Optional[str] = None


router = APIRouter()


@router.post(
    "/order",
    response_model=Order,
    status_code=201,
    summary="Создать заказ",
    description="Создаёт новый заказ. При отрицательной сумме вернёт 400."
)
@inject
async def create_order(
    order_data: OrderCreateRequest,
    service: OrderService = Depends(Provide[Container.order_service]),
):
    try:
        return await service.create_order(
            user_id=order_data.user_id,
            amount=order_data.amount,
            description=order_data.description,
        )
    except NegativeAmountError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/orders/{user_id}",
    response_model=List[Order],
    summary="Получить список заказов",
    description="Возвращает все заказы указанного пользователя."
)
@inject
async def list_orders(
    user_id: UUID,
    service: OrderService = Depends(Provide[Container.order_service]),
):
    return await service.get_orders(user_id)


@router.get(
    "/order/{order_id}",
    summary="Получить статус заказа",
    description="Отдаёт статус заказа по его UUID."
)
@inject
async def get_order_status(
    order_id: UUID,
    service: OrderService = Depends(Provide[Container.order_service]),
):
    """
    Получить статус заказа по его UUID.
    """
    status = await service.get_order_status(order_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return status
