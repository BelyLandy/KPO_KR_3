from enum import Enum


class EventType(Enum):
    """
    Перечисление типов событий:
    - ORDER_CREATED, ORDER_CANCELLED — для Order Service
    - PAYMENT_REQUEST, PAYMENT_RESPONSE — для Payment Service
    """
    # События сервиса заказов
    ORDER_CREATED   = "OrderCreated"
    ORDER_CANCELLED = "OrderCancelled"

    # События сервиса платежей
    PAYMENT_REQUEST  = "PaymentRequest"
    PAYMENT_RESPONSE = "PaymentResponse"

    def __str__(self) -> str:
        return self.value
