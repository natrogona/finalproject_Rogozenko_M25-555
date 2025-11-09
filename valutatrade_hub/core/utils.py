"""Вспомогательные функции для приложения ValutaTrade Hub."""

from typing import Dict

from valutatrade_hub.core.exceptions import ValidationError, RateNotAvailableError


def validate_currency_code(code: str) -> str:
    """
    Проверить и нормализовать код валюты.

    Args:
        code: Код валюты для проверки

    Returns:
        Нормализованный (в верхнем регистре) код валюты

    Raises:
        ValidationError: Если код недействителен
    """
    if not isinstance(code, str):
        raise ValidationError("Код валюты должен быть строкой")
    if not code or not code.strip():
        raise ValidationError("Код валюты не может быть пустым")

    code = code.strip().upper()

    if len(code) < 2 or len(code) > 5:
        raise ValidationError("Код валюты должен содержать от 2 до 5 символов")
    if " " in code:
        raise ValidationError("Код валюты не может содержать пробелы")

    return code


def validate_amount(amount: float, min_value: float = 0.0) -> None:
    """
    Проверить сумму транзакции.

    Args:
        amount: Сумма для проверки
        min_value: Минимально допустимое значение (по умолчанию 0.0)

    Raises:
        ValidationError: Если сумма недействительна
    """
    if not isinstance(amount, (int, float)):
        raise ValidationError("Сумма должна быть числом")
    if amount <= min_value:
        raise ValidationError(f"Сумма должна быть больше {min_value}")


def convert_currency(
    amount: float, from_currency: str, to_currency: str, rates: Dict[str, float]
) -> float:
    """
    Конвертировать сумму из одной валюты в другую.

    Args:
        amount: Сумма для конвертации
        from_currency: Код исходной валюты
        to_currency: Код целевой валюты
        rates: Словарь обменных курсов (пара_валют -> курс)

    Returns:
        Конвертированная сумма

    Raises:
        RateNotAvailableError: Если обменный курс не найден
        ValidationError: Если входные данные недействительны
    """
    validate_amount(amount, min_value=0.0)
    from_currency = validate_currency_code(from_currency)
    to_currency = validate_currency_code(to_currency)

    if from_currency == to_currency:
        return amount

    # Try direct conversion
    rate_key = f"{from_currency}_{to_currency}"
    if rate_key in rates:
        return amount * rates[rate_key]

    # Try inverse conversion
    inverse_key = f"{to_currency}_{from_currency}"
    if inverse_key in rates:
        return amount / rates[inverse_key]

    raise RateNotAvailableError(
        f"Обменный курс для {from_currency} в {to_currency} недоступен"
    )


def get_exchange_rate(
    from_currency: str, to_currency: str, rates: Dict[str, float]
) -> float:
    """
    Получить обменный курс между двумя валютами.

    Args:
        from_currency: Код исходной валюты
        to_currency: Код целевой валюты
        rates: Словарь обменных курсов

    Returns:
        Обменный курс

    Raises:
        RateNotAvailableError: Если курс не найден
    """
    from_currency = validate_currency_code(from_currency)
    to_currency = validate_currency_code(to_currency)

    if from_currency == to_currency:
        return 1.0

    # Try direct rate
    rate_key = f"{from_currency}_{to_currency}"
    if rate_key in rates:
        return rates[rate_key]

    # Try inverse rate
    inverse_key = f"{to_currency}_{from_currency}"
    if inverse_key in rates:
        return 1.0 / rates[inverse_key]

    raise RateNotAvailableError(
        f"Обменный курс для {from_currency} в {to_currency} недоступен"
    )
