"""Менеджер базы данных для хранения данных в JSON с использованием паттерна Singleton."""

import json
from pathlib import Path
from typing import Any
from valutatrade_hub.core.exceptions import DatabaseError


class DatabaseManager:
    """Singleton-менеджер базы данных для операций с JSON-файлами."""

    _instance = None
    _initialized = False

    def __new__(cls):
        """Обеспечить существование только одного экземпляра (паттерн Singleton)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Инициализация менеджера базы данных (только один раз)."""
        if not DatabaseManager._initialized:
            self._data_dir = Path("data")
            self._ensure_data_directory()
            DatabaseManager._initialized = True

    def _ensure_data_directory(self) -> None:
        """Создать директорию данных, если она не существует."""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise DatabaseError(f"Failed to create data directory: {e}")

    def _get_file_path(self, filename: str) -> Path:
        """
        Получить полный путь к файлу данных.

        Args:
            filename: Имя файла

        Returns:
            Объект Path для файла
        """
        return self._data_dir / filename

    def load(self, filename: str, default: Any = None) -> Any:
        """
        Загрузить данные из JSON-файла.

        Args:
            filename: Имя файла для загрузки
            default: Значение по умолчанию, если файл не существует

        Returns:
            Загруженные данные или значение по умолчанию

        Raises:
            DatabaseError: Если загрузка не удалась
        """
        file_path = self._get_file_path(filename)

        if not file_path.exists():
            if default is not None:
                return default
            raise DatabaseError(f"File {filename} not found")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise DatabaseError(f"Invalid JSON in {filename}: {e}")
        except Exception as e:
            raise DatabaseError(f"Failed to load {filename}: {e}")

    def save(self, filename: str, data: Any) -> None:
        """
        Сохранить данные в JSON-файл.

        Args:
            filename: Имя файла для сохранения
            data: Данные для сохранения (должны быть JSON-сериализуемыми)

        Raises:
            DatabaseError: Если сохранение не удалось
        """
        file_path = self._get_file_path(filename)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except TypeError as e:
            raise DatabaseError(f"Data is not JSON serializable: {e}")
        except Exception as e:
            raise DatabaseError(f"Failed to save {filename}: {e}")

    def file_exists(self, filename: str) -> bool:
        """
        Проверить, существует ли файл данных.

        Args:
            filename: Имя файла для проверки

        Returns:
            True, если файл существует, False в противном случае
        """
        return self._get_file_path(filename).exists()

    def initialize_file(self, filename: str, default_data: Any) -> None:
        """
        Инициализировать файл данными по умолчанию, если он не существует.

        Args:
            filename: Имя файла
            default_data: Данные по умолчанию для записи
        """
        if not self.file_exists(filename):
            self.save(filename, default_data)


# Вспомогательная функция для получения singleton-экземпляра
def get_db() -> DatabaseManager:
    """
    Получить singleton-экземпляр DatabaseManager.

    Returns:
        Экземпляр DatabaseManager
    """
    return DatabaseManager()
