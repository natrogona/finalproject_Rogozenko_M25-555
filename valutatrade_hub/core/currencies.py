"""Иерархия валют для управления фиатными и криптовалютами."""

from abc import ABC, abstractmethod
from valutatrade_hub.core.exceptions import ValidationError


class Currency(ABC):
    """Абстрактный базовый класс для всех типов валют."""

    def __init__(self, name: str, code: str):
        """
        Инициализация валюты.

        Args:
            name: Читаемое название (например, "US Dollar", "Bitcoin")
            code: ISO-код или тикер (например, "USD", "BTC")

        Raises:
            ValidationError: Если валидация не удалась
        """
        self._validate_code(code)
        self._validate_name(name)
        self._name = name
        self._code = code.upper()

    @staticmethod
    def _validate_code(code: str) -> None:
        """Проверить формат кода валюты."""
        if not isinstance(code, str):
            raise ValidationError("Currency code must be a string")
        if not code or not code.strip():
            raise ValidationError("Currency code cannot be empty")
        if len(code) < 2 or len(code) > 5:
            raise ValidationError("Currency code must be 2-5 characters")
        if " " in code:
            raise ValidationError("Currency code cannot contain spaces")
        if not code.replace("_", "").isalnum():
            raise ValidationError("Currency code must be alphanumeric")

    @staticmethod
    def _validate_name(name: str) -> None:
        """Проверить название валюты."""
        if not isinstance(name, str):
            raise ValidationError("Currency name must be a string")
        if not name or not name.strip():
            raise ValidationError("Currency name cannot be empty")

    @property
    def name(self) -> str:
        """Получить название валюты."""
        return self._name

    @property
    def code(self) -> str:
        """Получить код валюты."""
        return self._code

    @abstractmethod
    def get_display_info(self) -> str:
        """Вернуть строковое представление для UI/логов."""
        pass

    def __str__(self) -> str:
        """Строковое представление."""
        return f"{self.code} ({self.name})"

    def __repr__(self) -> str:
        """Представление для разработчиков."""
        return f"{self.__class__.__name__}(name='{self.name}', code='{self.code}')"


class FiatCurrency(Currency):
    """Представляет фиатную (традиционную государственную) валюту."""

    def __init__(self, name: str, code: str, issuing_country: str):
        """
        Инициализация фиатной валюты.

        Args:
            name: Название валюты
            code: Код валюты
            issuing_country: Страна или регион, выпускающий эту валюту

        Raises:
            ValidationError: Если валидация не удалась
        """
        super().__init__(name, code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValidationError("Issuing country must be a non-empty string")
        self._issuing_country = issuing_country

    @property
    def issuing_country(self) -> str:
        """Получить страну-эмитента."""
        return self._issuing_country

    def get_display_info(self) -> str:
        """Вернуть отформатированную информацию о фиатной валюте."""
        return f"[FIAT] {self.code} - {self.name} (Issuing: {self.issuing_country})"

    def __repr__(self) -> str:
        """Представление для разработчиков."""
        return (
            f"FiatCurrency(name='{self.name}', code='{self.code}', "
            f"issuing_country='{self.issuing_country}')"
        )


class CryptoCurrency(Currency):
    """Представляет криптовалюту."""

    def __init__(
        self, name: str, code: str, algorithm: str, market_cap: float = None
    ):
        """
        Инициализация криптовалюты.

        Args:
            name: Название валюты
            code: Тикер валюты
            algorithm: Алгоритм майнинга/консенсуса (например, "SHA-256", "Ethash")
            market_cap: Рыночная капитализация (None если неизвестна)

        Raises:
            ValidationError: Если валидация не удалась
        """
        super().__init__(name, code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValidationError("Algorithm must be a non-empty string")
        if market_cap is not None and (
            not isinstance(market_cap, (int, float)) or market_cap < 0
        ):
            raise ValidationError("Market cap must be a non-negative number or None")
        self._algorithm = algorithm
        self._market_cap = market_cap

    @property
    def algorithm(self) -> str:
        """Получить алгоритм консенсуса."""
        return self._algorithm

    @property
    def market_cap(self) -> float:
        """Получить рыночную капитализацию."""
        return self._market_cap

    def get_display_info(self) -> str:
        """Вернуть отформатированную информацию о криптовалюте."""
        mcap_info = (
            f"MCAP: {self.market_cap:.2e}" if self.market_cap else "MCAP: unknown"
        )
        return f"[CRYPTO] {self.code} - {self.name} (Algo: {self.algorithm}, {mcap_info})"

    def __repr__(self) -> str:
        """Представление для разработчиков."""
        return (
            f"CryptoCurrency(name='{self.name}', code='{self.code}', "
            f"algorithm='{self.algorithm}', market_cap={self.market_cap})"
        )


# Currency Registry
_CURRENCY_REGISTRY = {
    # Fiat currencies
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "GBP": FiatCurrency("British Pound", "GBP", "United Kingdom"),
    "JPY": FiatCurrency("Japanese Yen", "JPY", "Japan"),
    "CNY": FiatCurrency("Chinese Yuan", "CNY", "China"),
    "KRW": FiatCurrency("South Korean Won", "KRW", "South Korea"),
    # Cryptocurrencies
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", market_cap=1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", market_cap=4.5e11),
    "SOL": CryptoCurrency("Solana", "SOL", "Proof of History", market_cap=8.5e10),
}


def get_currency(code: str) -> Currency:
    """
    Получить экземпляр валюты из реестра по коду.

    Args:
        code: Код валюты (регистр не имеет значения)

    Returns:
        Экземпляр Currency

    Raises:
        CurrencyNotFoundError: Если код валюты отсутствует в реестре
    """
    from valutatrade_hub.core.exceptions import CurrencyNotFoundError

    code_upper = code.upper().strip()
    if code_upper not in _CURRENCY_REGISTRY:
        raise CurrencyNotFoundError(f"Unknown currency '{code}'")
    return _CURRENCY_REGISTRY[code_upper]


def get_supported_currencies() -> list:
    """
    Получить список всех поддерживаемых кодов валют.

    Returns:
        Список кодов валют
    """
    return list(_CURRENCY_REGISTRY.keys())
