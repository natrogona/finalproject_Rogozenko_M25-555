"""API clients for fetching exchange rates from external services."""

from abc import ABC, abstractmethod
from typing import Dict
import requests

from valutatrade_hub.logging_config import get_logger

logger = get_logger("api_clients")


class ApiRequestError(Exception):
    """Raised when an API request fails."""

    pass


class BaseApiClient(ABC):
    """Abstract base class for API clients."""

    def __init__(self, timeout: int = 10):
        """
        Initialize API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """
        Fetch exchange rates from the API.

        Returns:
            Dictionary mapping currency pairs to rates (e.g., {"BTC_USD": 59337.21})

        Raises:
            ApiRequestError: If the API request fails
        """
        pass

    def _handle_request_error(self, error: Exception, service_name: str) -> None:
        """
        Handle request errors uniformly.

        Args:
            error: The exception that occurred
            service_name: Name of the service for logging

        Raises:
            ApiRequestError: With formatted error message
        """
        error_msg = f"Failed to fetch rates from {service_name}: {str(error)}"
        logger.error(error_msg)
        raise ApiRequestError(error_msg)


class CoinGeckoClient(BaseApiClient):
    """Client for fetching cryptocurrency rates from CoinGecko API."""

    def __init__(
        self,
        base_url: str,
        crypto_id_map: Dict[str, str],
        vs_currency: str = "usd",
        api_key: str = None,
        timeout: int = 10,
    ):
        """
        Initialize CoinGecko client.

        Args:
            base_url: CoinGecko API base URL
            crypto_id_map: Mapping of currency codes to CoinGecko IDs
            vs_currency: Target currency for prices
            api_key: Optional API key for premium access
            timeout: Request timeout in seconds
        """
        super().__init__(timeout)
        self.base_url = base_url
        self.crypto_id_map = crypto_id_map
        self.vs_currency = vs_currency.lower()

        if api_key:
            self.session.headers.update({"x-cg-demo-api-key": api_key})

    def fetch_rates(self) -> Dict[str, float]:
        """
        Fetch cryptocurrency rates from CoinGecko.

        Returns:
            Dictionary mapping currency pairs to rates (e.g., {"BTC_USD": 59337.21})

        Raises:
            ApiRequestError: If the API request fails
        """
        try:
            # Build comma-separated list of crypto IDs
            crypto_ids = ",".join(self.crypto_id_map.values())

            params = {"ids": crypto_ids, "vs_currencies": self.vs_currency}

            logger.info(
                f"Fetching rates from CoinGecko for {len(self.crypto_id_map)} cryptocurrencies"
            )
            response = self.session.get(
                self.base_url, params=params, timeout=self.timeout
            )

            # Check for rate limiting
            if response.status_code == 429:
                raise ApiRequestError(
                    "CoinGecko rate limit exceeded. Please try again later."
                )

            response.raise_for_status()
            data = response.json()

            # Convert response to standardized format: CODE_USD -> rate
            rates = {}
            for code, coin_id in self.crypto_id_map.items():
                if coin_id in data and self.vs_currency in data[coin_id]:
                    pair_key = f"{code}_{self.vs_currency.upper()}"
                    rates[pair_key] = data[coin_id][self.vs_currency]

            logger.info(
                f"Successfully fetched {len(rates)} cryptocurrency rates from CoinGecko"
            )
            return rates

        except requests.exceptions.Timeout:
            self._handle_request_error(
                Exception(f"Request timed out after {self.timeout} seconds"),
                "CoinGecko",
            )
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "CoinGecko")
        except (KeyError, ValueError, TypeError) as e:
            self._handle_request_error(
                Exception(f"Failed to parse response: {str(e)}"), "CoinGecko"
            )


class ExchangeRateApiClient(BaseApiClient):
    """Client for fetching fiat currency rates from ExchangeRate-API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        base_currency: str = "USD",
        fiat_currencies: tuple = (),
        timeout: int = 10,
    ):
        """
        Initialize ExchangeRate-API client.

        Args:
            base_url: ExchangeRate-API base URL
            api_key: API key for authentication
            base_currency: Base currency for rate calculations
            fiat_currencies: Tuple of fiat currencies to track
            timeout: Request timeout in seconds
        """
        super().__init__(timeout)
        self.base_url = base_url
        self.api_key = api_key
        self.base_currency = base_currency.upper()
        self.fiat_currencies = fiat_currencies

        if not self.api_key:
            logger.warning(
                "ExchangeRate-API key not provided. Fiat rates will not be available."
            )

    def fetch_rates(self) -> Dict[str, float]:
        """
        Fetch fiat currency rates from ExchangeRate-API.

        Returns:
            Dictionary mapping currency pairs to rates (e.g., {"EUR_USD": 1.0786})

        Raises:
            ApiRequestError: If the API request fails
        """
        if not self.api_key:
            logger.warning("Skipping ExchangeRate-API: No API key provided")
            return {}

        try:
            url = f"{self.base_url}/{self.api_key}/latest/{self.base_currency}"

            logger.info(
                f"Fetching rates from ExchangeRate-API with base {self.base_currency}"
            )
            response = self.session.get(url, timeout=self.timeout)

            # Check for rate limiting
            if response.status_code == 429:
                raise ApiRequestError(
                    "ExchangeRate-API rate limit exceeded. Please try again later."
                )

            # Check for invalid API key
            if response.status_code == 403:
                raise ApiRequestError("Invalid ExchangeRate-API key")

            response.raise_for_status()
            data = response.json()

            # Check API response status
            if data.get("result") != "success":
                error_type = data.get("error-type", "Unknown error")
                raise ApiRequestError(f"ExchangeRate-API error: {error_type}")

            conversion_rates = data.get("conversion_rates", {})

            # Convert to standardized format: XXX_USD -> rate
            # conversion_rates[EUR] = 0.927 means 1 USD = 0.927 EUR
            # We want EUR_USD which means EUR to USD, so we need 1/0.927
            rates = {}
            for currency in self.fiat_currencies:
                if currency in conversion_rates and conversion_rates[currency] > 0:
                    # Inverse the rate to get XXX/USD
                    pair_key = f"{currency}_{self.base_currency}"
                    rates[pair_key] = 1.0 / conversion_rates[currency]

            logger.info(
                f"Successfully fetched {len(rates)} fiat rates from ExchangeRate-API"
            )
            return rates

        except requests.exceptions.Timeout:
            self._handle_request_error(
                Exception(f"Request timed out after {self.timeout} seconds"),
                "ExchangeRate-API",
            )
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "ExchangeRate-API")
        except (KeyError, ValueError, TypeError) as e:
            self._handle_request_error(
                Exception(f"Failed to parse response: {str(e)}"), "ExchangeRate-API"
            )
