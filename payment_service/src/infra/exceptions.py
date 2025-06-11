class DublicateAccountException(Exception):
    """ Исключение: попытка создать аккаунт, который уже существует. """
    DEFAULT_MESSAGE = "Account already exists."

    def __init__(self, message: str = None) -> None:
        error_msg = message or self.DEFAULT_MESSAGE
        super().__init__(error_msg)
        self.message = error_msg


class NegativeAmountError(Exception):
    """ Исключение: сумма заказа не может быть нулевой или отрицательной. """
    DEFAULT_MESSAGE = "Amount cannot be negative or zero."

    def __init__(self, message: str = None) -> None:
        error_msg = message or self.DEFAULT_MESSAGE
        super().__init__(error_msg)
        self.message = error_msg


class NoSuchAccountError(Exception):
    """ Исключение: запрашиваемый аккаунт не найден. """
    DEFAULT_MESSAGE = "No such account found."

    def __init__(self, message: str = None) -> None:
        error_msg = message or self.DEFAULT_MESSAGE
        super().__init__(error_msg)
        self.message = error_msg
