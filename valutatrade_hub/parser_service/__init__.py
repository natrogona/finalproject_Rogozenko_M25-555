"""
Parser Service - Exchange Rates Fetching and Storage

This service handles fetching, caching, and historical storage of exchange rates
from external APIs (CoinGecko for crypto, ExchangeRate-API for fiat).

Modules:
--------
- config.py: Configuration settings for API endpoints and currencies
- api_clients.py: API client implementations (CoinGeckoClient, ExchangeRateApiClient)
- storage.py: File storage operations for rates cache and history
- updater.py: Main coordinator for fetching and storing rates

Usage:
------
    from valutatrade_hub.parser_service.config import ParserConfig
    from valutatrade_hub.parser_service.api_clients import CoinGeckoClient, ExchangeRateApiClient
    from valutatrade_hub.parser_service.storage import RatesStorage
    from valutatrade_hub.parser_service.updater import RatesUpdater

    # Initialize
    config = ParserConfig()
    coingecko = CoinGeckoClient(config.COINGECKO_URL, config.CRYPTO_ID_MAP)
    exchangerate = ExchangeRateApiClient(config.EXCHANGERATE_API_URL, config.EXCHANGERATE_API_KEY)
    storage = RatesStorage(config.RATES_FILE_PATH, config.HISTORY_FILE_PATH)

    # Update rates
    updater = RatesUpdater({"coingecko": coingecko, "exchangerate": exchangerate}, storage)
    result = updater.run_update()

CLI Commands:
-------------
- update-rates [--source <coingecko|exchangerate>]: Fetch and update rates
- show-rates [--currency <CODE>] [--top <N>]: Display cached rates
"""

__version__ = "1.0.0"
__all__ = [
    "ParserConfig",
    "CoinGeckoClient",
    "ExchangeRateApiClient",
    "RatesStorage",
    "RatesUpdater",
]
