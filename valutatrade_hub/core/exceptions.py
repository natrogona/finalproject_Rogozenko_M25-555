"""Пользовательские исключения для платформы ValutaTrade Hub."""


class ValutaTradeError(Exception):
    """Базовое исключение для всех ошибок ValutaTrade Hub."""

    pass


class ValidationError(ValutaTradeError):
    """Возникает при неудачной валидации данных."""

    pass


class AuthenticationError(ValutaTradeError):
    """Возникает при неудачной аутентификации пользователя."""

    pass


class InsufficientFundsError(ValutaTradeError):
    """Возникает, когда в кошельке недостаточно средств для операции."""

    pass


class CurrencyNotFoundError(ValutaTradeError):
    """Возникает, когда валюта не найдена в системе."""

    pass


class WalletNotFoundError(ValutaTradeError):
    """Возникает, когда кошелек не найден в портфеле."""

    pass


class UserNotFoundError(ValutaTradeError):
    """Возникает, когда пользователь не найден в системе."""

    pass


class UserAlreadyExistsError(ValutaTradeError):
    """Возникает при попытке зарегистрировать уже существующее имя пользователя."""

    pass


class RateNotAvailableError(ValutaTradeError):
    """Возникает, когда обменный курс недоступен."""

    pass


class DatabaseError(ValutaTradeError):
    """Возникает при неудачных операциях с базой данных."""

    pass


class NotLoggedInError(ValutaTradeError):
    """Возникает, когда пользователь пытается выполнить действие, требующее входа в систему."""

    pass


class ApiRequestError(ValutaTradeError):
    """Возникает при неудачном запросе к внешнему API."""

    pass
