from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field


class Account(BaseModel):
    """ Данные аккаунта пользователя с информацией о балансе. """
    user_id: UUID = Field(
        ...,
        description="Уникальный идентификатор пользователя"
    )
    balance: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Текущий баланс аккаунта (неотрицательный)"
    )

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "balance": "150.75"
            }
        }