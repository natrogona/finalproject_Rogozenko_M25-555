"""Storage operations for exchange rates."""

import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from valutatrade_hub.logging_config import get_logger

logger = get_logger("storage")


class RatesStorage:
    """Handles reading and writing exchange rate data to JSON files."""

    def __init__(self, rates_file_path: str, history_file_path: str):
        """
        Initialize storage.

        Args:
            rates_file_path: Path to rates.json (current rates cache)
            history_file_path: Path to exchange_rates.json (historical data)
        """
        self.rates_file_path = Path(rates_file_path)
        self.history_file_path = Path(history_file_path)

        # Ensure parent directories exist
        self.rates_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_file_path.parent.mkdir(parents=True, exist_ok=True)

    def save_rates_cache(self, rates_data: Dict[str, Dict[str, any]]) -> None:
        """
        Save current rates to cache file (rates.json).

        Args:
            rates_data: Dictionary with rate pairs and metadata

        Format:
            {
                "pairs": {
                    "BTC_USD": {"rate": 59337.21, "updated_at": "...", "source": "CoinGecko"},
                    ...
                },
                "last_refresh": "2025-10-10T12:00:01Z"
            }
        """
        try:
            # Write atomically using temporary file
            temp_file = self.rates_file_path.with_suffix(".tmp")

            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(rates_data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(self.rates_file_path)

            logger.info(f"Saved rates cache to {self.rates_file_path}")

        except (IOError, OSError) as e:
            logger.error(f"Failed to save rates cache: {e}")
            raise

    def load_rates_cache(self) -> Optional[Dict[str, Dict[str, any]]]:
        """
        Load current rates from cache file.

        Returns:
            Dictionary with rates data or None if file doesn't exist

        Format:
            {
                "pairs": {
                    "BTC_USD": {"rate": 59337.21, "updated_at": "...", "source": "..."},
                    ...
                },
                "last_refresh": "2025-10-10T12:00:01Z"
            }
        """
        if not self.rates_file_path.exists():
            logger.warning(f"Rates cache file not found: {self.rates_file_path}")
            return None

        try:
            with open(self.rates_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.info(f"Loaded rates cache from {self.rates_file_path}")
            return data

        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load rates cache: {e}")
            return None

    def append_to_history(self, rate_entries: List[Dict[str, any]]) -> None:
        """
        Append new rate entries to historical data file.

        Args:
            rate_entries: List of rate entry dictionaries

        Entry format:
            {
                "id": "BTC_USD_2025-10-10T12:00:00Z",
                "from_currency": "BTC",
                "to_currency": "USD",
                "rate": 59337.21,
                "timestamp": "2025-10-10T12:00:00Z",
                "source": "CoinGecko",
                "meta": {...}
            }
        """
        try:
            # Load existing history or start with empty list
            history = []
            if self.history_file_path.exists():
                with open(self.history_file_path, "r", encoding="utf-8") as f:
                    history = json.load(f)

            # Get existing IDs to avoid duplicates
            existing_ids = {entry.get("id") for entry in history if "id" in entry}

            # Add only new entries
            new_entries = []
            for entry in rate_entries:
                if entry.get("id") not in existing_ids:
                    new_entries.append(entry)

            if new_entries:
                history.extend(new_entries)

                # Write atomically
                temp_file = self.history_file_path.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)

                temp_file.replace(self.history_file_path)

                logger.info(f"Appended {len(new_entries)} new entries to history")
            else:
                logger.info("No new entries to add to history")

        except (IOError, json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to append to history: {e}")
            raise

    def load_history(self, limit: Optional[int] = None) -> List[Dict[str, any]]:
        """
        Load historical rate data.

        Args:
            limit: Optional limit on number of recent entries to return

        Returns:
            List of historical rate entries
        """
        if not self.history_file_path.exists():
            logger.warning(f"History file not found: {self.history_file_path}")
            return []

        try:
            with open(self.history_file_path, "r", encoding="utf-8") as f:
                history = json.load(f)

            if limit and limit > 0:
                history = history[-limit:]

            logger.info(f"Loaded {len(history)} entries from history")
            return history

        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load history: {e}")
            return []

    @staticmethod
    def create_rate_entry(
        from_currency: str,
        to_currency: str,
        rate: float,
        timestamp: str,
        source: str,
        meta: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a standardized rate entry for historical storage.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            rate: Exchange rate
            timestamp: ISO format timestamp
            source: Data source (e.g., "CoinGecko")
            meta: Optional metadata

        Returns:
            Dictionary representing a rate entry
        """
        entry_id = f"{from_currency}_{to_currency}_{timestamp}"

        return {
            "id": entry_id,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate,
            "timestamp": timestamp,
            "source": source,
            "meta": meta or {},
        }

    def clear_cache(self) -> None:
        """Clear the rates cache file."""
        try:
            if self.rates_file_path.exists():
                self.rates_file_path.unlink()
                logger.info("Cleared rates cache")
        except OSError as e:
            logger.error(f"Failed to clear cache: {e}")

    def get_cache_age(self) -> Optional[int]:
        """
        Get age of cache file in seconds.

        Returns:
            Age in seconds, or None if file doesn't exist
        """
        if not self.rates_file_path.exists():
            return None

        try:
            mtime = self.rates_file_path.stat().st_mtime
            return int(datetime.now().timestamp() - mtime)
        except OSError:
            return None
