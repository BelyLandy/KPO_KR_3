from enum import Enum


class PaymentStatus(Enum):
    """
    Возможные статусы для платежей:
    - PENDING: ожидает обработки
    - SUCCESS: успешно завершён
    - FAILED: завершён с ошибкой
    """
    PENDING: str = "pending"
    SUCCESS: str = "success"
    FAILED:  str = "failed"

    def __str__(self) -> str:
        return self.value
