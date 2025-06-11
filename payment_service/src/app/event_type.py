from enum import Enum


class EventType(Enum):
    ORDER_CREATED   = "OrderCreated"
    ORDER_CANCELLED = "OrderCancelled"

    PAYMENT_REQUEST  = "PaymentRequest"
    PAYMENT_RESPONSE = "PaymentResponse"

    def __str__(self) -> str:
        return self.value
