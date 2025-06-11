from enum import Enum


class PaymentStatus(Enum):
    PENDING: str = "pending"
    SUCCESS: str = "success"
    FAILED:  str = "failed"

    def __str__(self) -> str:
        return self.value
