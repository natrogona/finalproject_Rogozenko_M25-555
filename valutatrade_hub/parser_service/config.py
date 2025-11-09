"""Configuration for Parser Service."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ParserConfig:
    """Configuration class for Parser Service."""

    # API Keys (loaded from environment variables)
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")
    COINGECKO_API_KEY: str = os.getenv("COINGECKO_API_KEY", "")

    # API Endpoints
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Base currency for all operations
    BASE_CURRENCY: str = "USD"

    # Supported fiat currencies
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")

    # Supported cryptocurrencies
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")

    # Mapping of currency codes to CoinGecko IDs
    CRYPTO_ID_MAP: dict = None

    # File paths
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    # Network parameters
    REQUEST_TIMEOUT: int = 10

    # Cache TTL (time to live) in seconds - 1 hour
    CACHE_TTL: int = 3600

    def __post_init__(self):
        """Initialize crypto ID map after dataclass initialization."""
        if self.CRYPTO_ID_MAP is None:
            self.CRYPTO_ID_MAP = {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "SOL": "solana",
            }

        # Convert relative paths to absolute paths
        project_root = Path(__file__).parent.parent.parent
        self.RATES_FILE_PATH = str(project_root / self.RATES_FILE_PATH)
        self.HISTORY_FILE_PATH = str(project_root / self.HISTORY_FILE_PATH)

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.EXCHANGERATE_API_KEY:
            print(
                "Warning: EXCHANGERATE_API_KEY is not set. Fiat rates will not be available."
            )
            return False
        return True
