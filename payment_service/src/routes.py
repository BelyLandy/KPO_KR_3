from typing import Optional, Dict
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from dependency_injector.wiring import inject, Provide

from src.dependencies import Container
from src.infra.services.payment_service import PaymentService
from src.app.account import Account as AccountDomain
from src.infra.exceptions import (
    DublicateAccountException,
    NegativeAmountError,
    NoSuchAccountError,
)


router = APIRouter(prefix="/accounts", tags=["Accounts"])


class AccountCreateRequest(BaseModel):
    """Тело запроса для создания аккаунта."""
    user_id: UUID = Field(..., description="UUID пользователя")


class BalanceUpdateRequest(BaseModel):
    """Тело запроса для пополнения баланса."""
    amount: Decimal = Field(
        ...,
        description="Сумма пополнения (строго > 0)"
    )


class AccountResponse(BaseModel):
    """Ответ с информацией об аккаунте."""
    user_id: UUID
    balance: Decimal


@router.post(
    "",
    response_model=AccountResponse,
    status_code=201,
    summary="Создать аккаунт"
)
@inject
async def create_account(
    data: AccountCreateRequest,
    service: PaymentService = Depends(Provide[Container.payment_service])
) -> AccountResponse:
    """
    Создает аккаунт для пользователя. Если аккаунт уже есть, возвращает 400.
    """
    try:
        account: AccountDomain = await service.create_account(data.user_id)
    except DublicateAccountException as exc:
        raise HTTPException(status_code=400, detail=exc.message)

    return AccountResponse(
        user_id=account.user_id,
        balance=account.balance
    )


@router.post(
    "/{user_id}/increment",
    response_model=AccountResponse,
    summary="Пополнить баланс"
)
@inject
async def update_balance(
    user_id: UUID,
    data: BalanceUpdateRequest,
    service: PaymentService = Depends(Provide[Container.payment_service])
) -> AccountResponse:
    """
    Пополняет баланс указанного пользователя.
    404, если аккаунта нет; 400, если сумма некорректна.
    """
    # Проверяем, что аккаунт существует
    try:
        await service.get_account_balance(user_id)
    except NoSuchAccountError as exc:
        raise HTTPException(status_code=404, detail=exc.message)

    # Выполняем пополнение
    try:
        await service.update_account_balance(user_id, data.amount)
    except NegativeAmountError as exc:
        raise HTTPException(status_code=400, detail=exc.message)

    # Получаем обновленные данные
    updated: Optional[Dict] = await service.get_account_balance(user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Аккаунт не найден после обновления")

    return AccountResponse(**updated)


@router.get(
    "/{user_id}",
    response_model=AccountResponse,
    summary="Получить баланс"
)
@inject
async def get_balance(
    user_id: UUID,
    service: PaymentService = Depends(Provide[Container.payment_service])
) -> AccountResponse:
    """
    Возвращает текущий баланс пользователя.
    404, если аккаунта нет.
    """
    try:
        info: Optional[Dict] = await service.get_account_balance(user_id)
    except NoSuchAccountError as exc:
        raise HTTPException(status_code=404, detail=exc.message)

    return AccountResponse(**info)
