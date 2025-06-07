from enum import Enum

class Status(Enum):
    """Возможные статусы заказа."""

    NEW: str = "new"
    FINISHED: str = "finished"
    CANCELED: str = "canceled"

    def __str__(self) -> str:
        return self.value
