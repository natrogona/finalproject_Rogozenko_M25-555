"""Основные модели данных для платформы ValutaTrade Hub."""

import hashlib
import secrets
from datetime import datetime
from typing import Dict, Optional
from valutatrade_hub.core.exceptions import (
    ValidationError,
    InsufficientFundsError,
    WalletNotFoundError,
)


class User:
    """Представляет пользователя в системе с возможностями аутентификации."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ):
        """
        Инициализация пользователя.

        Args:
            user_id: Уникальный идентификатор пользователя
            username: Имя пользователя (должно быть непустым)
            hashed_password: Хэшированный пароль
            salt: Соль для хэширования пароля
            registration_date: Дата регистрации пользователя

        Raises:
            ValidationError: Если валидация не удалась
        """
        self._user_id = user_id
        self.username = username  # Uses setter for validation
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        """Получить ID пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Получить имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Установить имя пользователя с валидацией."""
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("Имя пользователя не может быть пустым")
        self._username = value

    @property
    def hashed_password(self) -> str:
        """Получить хэшированный пароль."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Получить соль."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Получить дату регистрации."""
        return self._registration_date

    def verify_password(self, password: str) -> bool:
        """
        Проверить, соответствует ли предоставленный пароль сохраненному хэшу.

        Args:
            password: Пароль для проверки

        Returns:
            True, если пароль совпадает, False в противном случае
        """
        return self._hash_password(password, self._salt) == self._hashed_password

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """
        Хэшировать пароль с солью, используя SHA-256.

        Args:
            password: Пароль в виде простого текста
            salt: Строка соли

        Returns:
            Хэш в шестнадцатеричном формате
        """
        combined = password + salt
        return hashlib.sha256(combined.encode()).hexdigest()

    @classmethod
    def create_new(cls, user_id: int, username: str, password: str) -> "User":
        """
        Фабричный метод для создания нового пользователя с хэшированием пароля.

        Args:
            user_id: Уникальный идентификатор пользователя
            username: Желаемое имя пользователя
            password: Пароль в виде простого текста

        Returns:
            Новый экземпляр User

        Raises:
            ValidationError: Если валидация не удалась
        """
        if len(password) < 4:
            raise ValidationError("Пароль должен содержать не менее 4 символов")
        salt = secrets.token_hex(8)
        hashed = cls._hash_password(password, salt)
        return cls(
            user_id=user_id,
            username=username,
            hashed_password=hashed,
            salt=salt,
            registration_date=datetime.now(),
        )

    def to_dict(self) -> dict:
        """Преобразовать пользователя в словарь для хранения в JSON."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "hashed_password": self.hashed_password,
            "salt": self.salt,
            "registration_date": self.registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Создать экземпляр User из словаря."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
        )


class Wallet:
    """Представляет кошелек для конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        """
        Инициализация кошелька.

        Args:
            currency_code: Код валюты (например, "USD", "BTC")
            balance: Начальный баланс (по умолчанию 0.0)

        Raises:
            ValidationError: Если валидация не удалась
        """
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValidationError("Код валюты должен быть непустой строкой")
        self._currency_code = currency_code.upper()
        self.balance = balance  # Uses setter for validation

    @property
    def currency_code(self) -> str:
        """Получить код валюты."""
        return self._currency_code

    @property
    def balance(self) -> float:
        """Получить текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """
        Установить баланс с валидацией.

        Args:
            value: Новая сумма баланса

        Raises:
            ValidationError: Если значение отрицательное или неверный тип
        """
        if not isinstance(value, (int, float)):
            raise ValidationError("Баланс должен быть числом")
        if value < 0:
            raise ValidationError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """
        Добавить средства в кошелек.

        Args:
            amount: Сумма для пополнения

        Raises:
            ValidationError: Если сумма не положительная
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError("Сумма депозита должна быть положительным числом")
        self._balance += amount

    def withdraw(self, amount: float) -> None:
        """
        Снять средства с кошелька.

        Args:
            amount: Сумма для вывода

        Raises:
            ValidationError: Если сумма не положительная
            InsufficientFundsError: Если баланс недостаточен
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError("Сумма вывода должна быть положительным числом")
        if amount > self._balance:
            raise InsufficientFundsError(
                f"Недостаточно средств в кошельке {self.currency_code}. "
                f"Доступно: {self.balance:.4f}, Требуется: {amount:.4f}"
            )
        self._balance -= amount

    def to_dict(self) -> dict:
        """Преобразовать кошелек в словарь для хранения в JSON."""
        return {"currency_code": self.currency_code, "balance": self.balance}

    @classmethod
    def from_dict(cls, data: dict) -> "Wallet":
        """Создать экземпляр Wallet из словаря."""
        return cls(currency_code=data["currency_code"], balance=data["balance"])

    def __repr__(self) -> str:
        """Представление для разработчиков."""
        return f"Wallet(currency_code='{self.currency_code}', balance={self.balance})"


class Portfolio:
    """Управляет несколькими кошельками для одного пользователя."""

    def __init__(self, user_id: int, wallets: Optional[Dict[str, Wallet]] = None):
        """
        Инициализация портфеля.

        Args:
            user_id: ID пользователя-владельца портфеля
            wallets: Словарь кошельков (код_валюты -> Wallet)

        Raises:
            ValidationError: Если валидация не удалась
        """
        if not isinstance(user_id, int):
            raise ValidationError("ID пользователя должен быть целым числом")
        self._user_id = user_id
        self._wallets: Dict[str, Wallet] = wallets if wallets is not None else {}

    @property
    def user_id(self) -> int:
        """Получить ID пользователя."""
        return self._user_id

    @property
    def wallets(self) -> Dict[str, Wallet]:
        """Получить копию словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """
        Добавить новый кошелек валюты в портфель.

        Args:
            currency_code: Код валюты для добавления

        Returns:
            Новый или существующий кошелек

        Raises:
            ValidationError: Если код валюты недействителен
        """
        currency_code = currency_code.upper()
        if currency_code in self._wallets:
            return self._wallets[currency_code]
        wallet = Wallet(currency_code)
        self._wallets[currency_code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        """
        Получить кошелек для конкретной валюты.

        Args:
            currency_code: Код валюты

        Returns:
            Экземпляр Wallet

        Raises:
            WalletNotFoundError: Если кошелек не существует
        """
        currency_code = currency_code.upper()
        if currency_code not in self._wallets:
            raise WalletNotFoundError(f"Кошелек для {currency_code} не найден")
        return self._wallets[currency_code]

    def has_wallet(self, currency_code: str) -> bool:
        """
        Проверить, есть ли в портфеле кошелек для данной валюты.

        Args:
            currency_code: Код валюты для проверки

        Returns:
            True, если кошелек существует, False в противном случае
        """
        return currency_code.upper() in self._wallets

    def to_dict(self) -> dict:
        """Преобразовать портфель в словарь для хранения в JSON."""
        return {
            "user_id": self.user_id,
            "wallets": {
                code: wallet.to_dict() for code, wallet in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Portfolio":
        """Создать экземпляр Portfolio из словаря."""
        wallets = {
            code: Wallet.from_dict(wallet_data)
            for code, wallet_data in data.get("wallets", {}).items()
        }
        return cls(user_id=data["user_id"], wallets=wallets)

    def __repr__(self) -> str:
        """Представление для разработчиков."""
        return f"Portfolio(user_id={self.user_id}, wallets={len(self._wallets)})"
