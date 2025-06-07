from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.app.status import Status

class Order(BaseModel):
    """
    Модель данных заказа.
    """
    id: UUID = Field(
        ...,
        description="Уникальный идентификатор заказа"
    )
    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, создавшего заказ"
    )
    amount: Decimal = Field(
        ...,
        gt=0,
        description="Сумма заказа"
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Текстовое описание заказа"
    )
    status: Status = Field(
        ...,
        description="Текущий статус заказа"
    )

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "userId": "1c9a9a13-4a08-4d27-8ad2-9f8e2e7f3f2f",
                "amount": "123.45",
                "description": "First test order",
                "status": "NEW"
            }
        }
