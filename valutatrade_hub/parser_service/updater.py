"""Main updater module for fetching and storing exchange rates."""

from datetime import datetime
from typing import Dict, List, Optional

from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.api_clients import BaseApiClient, ApiRequestError
from valutatrade_hub.parser_service.storage import RatesStorage

logger = get_logger("updater")


class RatesUpdater:
    """Coordinates the process of fetching and storing exchange rates."""

    def __init__(self, clients: Dict[str, BaseApiClient], storage: RatesStorage):
        """
        Initialize the updater.

        Args:
            clients: Dictionary mapping source names to API clients
                    e.g., {"coingecko": CoinGeckoClient(...), "exchangerate": ExchangeRateApiClient(...)}
            storage: Storage instance for saving data
        """
        self.clients = clients
        self.storage = storage

    def run_update(self, source_filter: Optional[str] = None) -> Dict[str, any]:
        """
        Run the update process to fetch and store rates.

        Args:
            source_filter: Optional source name to update only from specific client

        Returns:
            Dictionary with update results and statistics

        Format:
            {
                "success": True,
                "total_rates": 6,
                "rates_by_source": {"coingecko": 3, "exchangerate": 3},
                "errors": [],
                "timestamp": "2025-10-10T15:30:00Z"
            }
        """
        logger.info("Starting exchange rates update")

        timestamp = datetime.utcnow().isoformat() + "Z"
        all_rates = {}
        errors = []
        rates_by_source = {}

        # Filter clients if source_filter is provided
        clients_to_use = self.clients
        if source_filter:
            if source_filter in self.clients:
                clients_to_use = {source_filter: self.clients[source_filter]}
                logger.info(f"Filtering to source: {source_filter}")
            else:
                error_msg = f"Unknown source: {source_filter}. Available: {list(self.clients.keys())}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "total_rates": 0,
                    "rates_by_source": {},
                    "errors": [error_msg],
                    "timestamp": timestamp,
                }

        # Fetch rates from each client
        for source_name, client in clients_to_use.items():
            try:
                logger.info(f"Fetching rates from {source_name}...")
                rates = client.fetch_rates()

                if rates:
                    all_rates.update(rates)
                    rates_by_source[source_name] = len(rates)
                    logger.info(f"Fetched {len(rates)} rates from {source_name}")
                else:
                    logger.warning(f"No rates returned from {source_name}")
                    rates_by_source[source_name] = 0

            except ApiRequestError as e:
                error_msg = f"{source_name}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                rates_by_source[source_name] = 0

            except Exception as e:
                error_msg = f"{source_name}: Unexpected error - {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                rates_by_source[source_name] = 0

        # Check if we got any rates
        if not all_rates:
            logger.error("No rates were fetched from any source")
            return {
                "success": False,
                "total_rates": 0,
                "rates_by_source": rates_by_source,
                "errors": errors or ["No rates fetched from any source"],
                "timestamp": timestamp,
            }

        # Save to cache (rates.json)
        try:
            cache_data = self._build_cache_data(all_rates, timestamp, rates_by_source)
            self.storage.save_rates_cache(cache_data)
            logger.info(f"Saved {len(all_rates)} rates to cache")
        except Exception as e:
            error_msg = f"Failed to save cache: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)

        # Save to history (exchange_rates.json)
        try:
            history_entries = self._build_history_entries(
                all_rates, timestamp, rates_by_source
            )
            self.storage.append_to_history(history_entries)
            logger.info(f"Appended {len(history_entries)} entries to history")
        except Exception as e:
            error_msg = f"Failed to save history: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)

        success = len(all_rates) > 0 and len(errors) == 0

        if success:
            logger.info(f"Update completed successfully. Total rates: {len(all_rates)}")
        else:
            logger.warning(
                f"Update completed with errors. Total rates: {len(all_rates)}, errors: {len(errors)}"
            )

        return {
            "success": success,
            "total_rates": len(all_rates),
            "rates_by_source": rates_by_source,
            "errors": errors,
            "timestamp": timestamp,
        }

    def _build_cache_data(
        self, rates: Dict[str, float], timestamp: str, rates_by_source: Dict[str, int]
    ) -> Dict[str, any]:
        """
        Build cache data structure for rates.json.

        Args:
            rates: Dictionary of rate pairs to values
            timestamp: ISO format timestamp
            rates_by_source: Count of rates per source

        Returns:
            Cache data structure
        """
        pairs = {}

        for pair_key, rate in rates.items():
            # Determine source based on currency type
            # Simple heuristic: if pair starts with BTC, ETH, SOL -> CoinGecko
            source = (
                "CoinGecko"
                if any(pair_key.startswith(crypto) for crypto in ["BTC", "ETH", "SOL"])
                else "ExchangeRate-API"
            )

            pairs[pair_key] = {"rate": rate, "updated_at": timestamp, "source": source}

        return {
            "pairs": pairs,
            "last_refresh": timestamp,
            "summary": {"total_pairs": len(pairs), "rates_by_source": rates_by_source},
        }

    def _build_history_entries(
        self, rates: Dict[str, float], timestamp: str, rates_by_source: Dict[str, int]
    ) -> List[Dict[str, any]]:
        """
        Build history entries for exchange_rates.json.

        Args:
            rates: Dictionary of rate pairs to values
            timestamp: ISO format timestamp
            rates_by_source: Count of rates per source

        Returns:
            List of history entry dictionaries
        """
        entries = []

        for pair_key, rate in rates.items():
            # Split pair into from_currency and to_currency
            parts = pair_key.split("_")
            if len(parts) != 2:
                logger.warning(f"Invalid pair format: {pair_key}")
                continue

            from_currency, to_currency = parts

            # Determine source
            source = (
                "CoinGecko"
                if any(from_currency == crypto for crypto in ["BTC", "ETH", "SOL"])
                else "ExchangeRate-API"
            )

            entry = self.storage.create_rate_entry(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                timestamp=timestamp,
                source=source,
                meta={"pair_key": pair_key, "rates_count_by_source": rates_by_source},
            )

            entries.append(entry)

        return entries
