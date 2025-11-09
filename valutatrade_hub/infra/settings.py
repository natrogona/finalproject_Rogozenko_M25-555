"""Загрузчик настроек с использованием паттерна Singleton для управления конфигурацией."""

import json
from pathlib import Path
from typing import Any, Dict


class SettingsLoader:
    """Singleton-загрузчик настроек для конфигурации приложения."""

    _instance = None
    _initialized = False

    # Выбран __new__ для singleton из-за простоты и читаемости
    def __new__(cls):
        """Обеспечить существование только одного экземпляра (паттерн Singleton)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Инициализация загрузчика настроек (только один раз)."""
        if not SettingsLoader._initialized:
            self._settings: Dict[str, Any] = self._load_settings()
            SettingsLoader._initialized = True

    def _get_default_settings(self) -> Dict[str, Any]:
        """
        Получить настройки по умолчанию.

        Returns:
            Словарь настроек по умолчанию
        """
        return {
            # Имена файлов
            "users_file": "users.json",
            "portfolios_file": "portfolios.json",
            "rates_file": "rates.json",
            # Настройки приложения
            "base_currency": "USD",
            "min_password_length": 4,
            "max_username_length": 50,
            # Настройки отображения
            "decimal_places": 4,
            # Настройки кеша курсов (в секундах)
            "rates_cache_ttl": 3600,  # 1 час
            # Настройки логирования
            "log_level": "INFO",
            "log_file": "valutatrade.log",
            "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "log_max_bytes": 10485760,  # 10MB
            "log_backup_count": 5,
        }

    def _load_from_pyproject(self) -> Dict[str, Any]:
        """
        Загрузить настройки из pyproject.toml секции [tool.valutatrade].

        Returns:
            Словарь настроек из pyproject.toml или пустой словарь
        """
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return {}

        pyproject_path = Path("pyproject.toml")
        if pyproject_path.exists():
            try:
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    return data.get("tool", {}).get("valutatrade", {})
            except Exception:
                pass
        return {}

    def _load_settings(self) -> Dict[str, Any]:
        """
        Загрузить настройки с приоритетом: pyproject.toml -> config.json -> defaults.

        Returns:
            Словарь объединенных настроек
        """
        # Начинаем с настроек по умолчанию
        settings = self._get_default_settings()

        # Пытаемся загрузить из pyproject.toml
        pyproject_settings = self._load_from_pyproject()
        if pyproject_settings:
            settings.update(pyproject_settings)
            return settings

        return settings

    def get(self, key: str, default: Any = None) -> Any:
        """
        Получить значение настройки.

        Args:
            key: Ключ настройки
            default: Значение по умолчанию, если ключ не найден

        Returns:
            Значение настройки или значение по умолчанию
        """
        return self._settings.get(key, default)

    @property
    def users_file(self) -> str:
        """Получить имя файла пользователей."""
        return self.get("users_file")

    @property
    def portfolios_file(self) -> str:
        """Получить имя файла портфелей."""
        return self.get("portfolios_file")

    @property
    def rates_file(self) -> str:
        """Получить имя файла курсов."""
        return self.get("rates_file")

    @property
    def base_currency(self) -> str:
        """Получить базовую валюту."""
        return self.get("base_currency")

    @property
    def min_password_length(self) -> int:
        """Получить минимальную длину пароля."""
        return self.get("min_password_length")

    @property
    def decimal_places(self) -> int:
        """Получить количество десятичных знаков для отображения."""
        return self.get("decimal_places")

    @property
    def rates_cache_ttl(self) -> int:
        """Получить время жизни кеша курсов в секундах."""
        return self.get("rates_cache_ttl")


# Вспомогательная функция для получения singleton-экземпляра
def get_settings() -> SettingsLoader:
    """
    Получить singleton-экземпляр SettingsLoader.

    Returns:
        Экземпляр SettingsLoader
    """
    return SettingsLoader()
