from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    """
    Запрос на создание аккаунта с указанием начального баланса.
    """
    user_id: UUID = Field(
        ...,
        description="Уникальный UUID пользователя"
    )
    initial_balance: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="Начальный баланс (>= 0.00)"
    )


class AccountTopUp(BaseModel):
    """
    Запрос на пополнение баланса аккаунта.
    """
    amount: Decimal = Field(
        ...,
        gt=0,
        description="Сумма пополнения (строго > 0.00)"
    )


class AccountRead(BaseModel):
    """
    Ответ с информацией об аккаунте и текущем балансе.
    """
    user_id: UUID = Field(
        ...,
        description="UUID пользователя"
    )
    balance: Decimal = Field(
        ...,
        description="Текущий баланс аккаунта"
    )

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "balance": "150.75"
            }
        }
