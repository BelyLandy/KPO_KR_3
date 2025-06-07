from typing import Optional

class NegativeAmountError(Exception):
    """
    Исключение: сумма заказа не может быть нулевой или отрицательной.
    """

    DEFAULT_MESSAGE = "Amount cannot be negative or zero."

    def __init__(self, message: Optional[str] = None) -> None:
        """
        :param message: Текст ошибки; если не задан, используется DEFAULT_MESSAGE.
        """
        final_message = message or self.DEFAULT_MESSAGE
        super().__init__(final_message)
        self.message = final_message
