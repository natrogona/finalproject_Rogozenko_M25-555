"""Слой бизнес-логики для приложения ValutaTrade Hub."""

from typing import Dict, Optional, Tuple
from datetime import datetime, timezone

from valutatrade_hub.core.models import User, Portfolio, Wallet
from valutatrade_hub.core.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    AuthenticationError,
    NotLoggedInError,
    RateNotAvailableError,
)
from valutatrade_hub.core.utils import (
    validate_currency_code,
    validate_amount,
    convert_currency,
    get_exchange_rate,
)
from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.infra.database import get_db
from valutatrade_hub.infra.settings import get_settings
from valutatrade_hub.decorators import log_action
from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.core.exceptions import ApiRequestError

logger = get_logger("usecases")


class TradingSession:
    """Управляет текущей пользовательской сессией."""

    def __init__(self):
        """Инициализация торговой сессии."""
        self._current_user: Optional[User] = None
        self._current_portfolio: Optional[Portfolio] = None

    @property
    def current_user(self) -> Optional[User]:
        """Получить текущего вошедшего пользователя."""
        return self._current_user

    @property
    def current_portfolio(self) -> Optional[Portfolio]:
        """Получить портфель текущего пользователя."""
        return self._current_portfolio

    def is_logged_in(self) -> bool:
        """Проверить, вошел ли пользователь в систему."""
        return self._current_user is not None

    def login(self, user: User, portfolio: Portfolio) -> None:
        """Установить текущего пользователя и портфель."""
        self._current_user = user
        self._current_portfolio = portfolio
        logger.info(f"User '{user.username}' logged in")

    def logout(self) -> None:
        """Очистить текущую сессию."""
        if self._current_user:
            logger.info(f"User '{self._current_user.username}' logged out")
        self._current_user = None
        self._current_portfolio = None

    def require_login(self) -> Tuple[User, Portfolio]:
        """
        Убедиться, что пользователь вошел в систему.

        Returns:
            Кортеж (пользователь, портфель)

        Raises:
            NotLoggedInError: Если пользователь не вошел в систему
        """
        if not self.is_logged_in():
            raise NotLoggedInError(
                "Сначала нужно войти в систему. Используйте: login --username <имя> --password <пароль>"
            )
        return self._current_user, self._current_portfolio


# Global session instance
_session = TradingSession()


def get_session() -> TradingSession:
    """Получить глобальную торговую сессию."""
    return _session


# Функции управления пользователями


@log_action("User Registration")
def register_user(username: str, password: str) -> User:
    """
    Зарегистрировать нового пользователя.

    Args:
        username: Желаемое имя пользователя
        password: Пароль пользователя

    Returns:
        Созданный экземпляр User

    Raises:
        UserAlreadyExistsError: Если имя пользователя уже существует
        ValidationError: Если валидация входных данных не удалась
    """
    db = get_db()
    settings = get_settings()

    # Load existing users
    users_data = db.load(settings.users_file, default=[])

    # Check if username already exists
    for user_data in users_data:
        if user_data["username"] == username:
            raise UserAlreadyExistsError(f"Имя пользователя '{username}' уже занято")

    # Generate new user ID
    new_id = max([u["user_id"] for u in users_data], default=0) + 1

    # Create new user
    user = User.create_new(new_id, username, password)

    # Save to database
    users_data.append(user.to_dict())
    db.save(settings.users_file, users_data)

    # Create empty portfolio
    portfolios_data = db.load(settings.portfolios_file, default=[])
    portfolio = Portfolio(new_id)
    portfolios_data.append(portfolio.to_dict())
    db.save(settings.portfolios_file, portfolios_data)

    logger.info(f"User '{username}' registered successfully with ID {new_id}")
    return user


@log_action("User Login")
def login_user(username: str, password: str) -> Tuple[User, Portfolio]:
    """
    Аутентифицировать и войти в систему.

    Args:
        username: Имя пользователя
        password: Пароль

    Returns:
        Кортеж (User, Portfolio)

    Raises:
        UserNotFoundError: Если пользователь не существует
        AuthenticationError: Если пароль неверен
    """
    db = get_db()
    settings = get_settings()

    # Load users
    users_data = db.load(settings.users_file, default=[])

    # Find user
    user_data = None
    for u in users_data:
        if u["username"] == username:
            user_data = u
            break

    if not user_data:
        raise UserNotFoundError(f"Пользователь '{username}' не найден")

    # Create User instance and verify password
    user = User.from_dict(user_data)
    if not user.verify_password(password):
        raise AuthenticationError("Неверный пароль")

    # Load portfolio
    portfolios_data = db.load(settings.portfolios_file, default=[])
    portfolio_data = None
    for p in portfolios_data:
        if p["user_id"] == user.user_id:
            portfolio_data = p
            break

    if not portfolio_data:
        # Create portfolio if it doesn't exist
        portfolio = Portfolio(user.user_id)
        portfolios_data.append(portfolio.to_dict())
        db.save(settings.portfolios_file, portfolios_data)
    else:
        portfolio = Portfolio.from_dict(portfolio_data)

    # Set session
    _session.login(user, portfolio)

    logger.info(f"User '{username}' logged in successfully")
    return user, portfolio


def logout_user() -> None:
    """Выйти из системы."""
    _session.logout()


# Функции управления портфелем


def get_current_portfolio() -> Portfolio:
    """
    Получить портфель текущего пользователя.

    Returns:
        Экземпляр Portfolio

    Raises:
        NotLoggedInError: Если пользователь не вошел в систему
    """
    _, portfolio = _session.require_login()
    return portfolio


def save_portfolio(portfolio: Portfolio) -> None:
    """
    Сохранить портфель в базу данных.

    Args:
        portfolio: Портфель для сохранения
    """
    db = get_db()
    settings = get_settings()

    portfolios_data = db.load(settings.portfolios_file, default=[])

    # Update or add portfolio
    found = False
    for i, p in enumerate(portfolios_data):
        if p["user_id"] == portfolio.user_id:
            portfolios_data[i] = portfolio.to_dict()
            found = True
            break

    if not found:
        portfolios_data.append(portfolio.to_dict())

    db.save(settings.portfolios_file, portfolios_data)


# Торговые функции


def load_rates() -> Dict[str, float]:
    """
    Загрузить обменные курсы из базы данных.

    Returns:
        Словарь курсов
    """
    db = get_db()
    settings = get_settings()

    rates_data = db.load(settings.rates_file, default={})

    rates = {}

    for key, value in rates_data["pairs"].items():
        if isinstance(value, dict) and "rate" in value:
            rates[key] = value["rate"]

    return rates


@log_action("Buy Currency")
def buy_currency(currency_code: str, amount: float) -> Tuple[Wallet, float]:
    """
    Купить валюту и добавить в портфель.

    Args:
        currency_code: Код валюты для покупки
        amount: Сумма для покупки

    Returns:
        Кортеж (обновленный кошелек, ориентировочная стоимость в базовой валюте)

    Raises:
        NotLoggedInError: Если пользователь не вошел в систему
        ValidationError: Если входные данные недействительны
        CurrencyNotFoundError: Если валюта не поддерживается
        RateNotAvailableError: Если обменный курс недоступен
    """
    user, portfolio = _session.require_login()

    # Validate inputs
    currency = get_currency(currency_code)  # Validates currency exists
    currency_code = currency.code
    validate_amount(amount)

    # Load rates and settings
    rates = load_rates()
    settings = get_settings()
    base_currency = settings.base_currency

    # Check if currency rate exists (unless it's base currency)
    if currency_code != base_currency:
        # This will raise RateNotAvailableError if rate doesn't exist
        try:
            get_exchange_rate(currency_code, base_currency, rates)
        except RateNotAvailableError:
            raise RateNotAvailableError(
                f"Невозможно купить {currency_code}: обменный курс недоступен. "
                f"Выполните 'update-rates' для получения текущих курсов."
            )

    # Get or create wallet
    if not portfolio.has_wallet(currency_code):
        portfolio.add_currency(currency_code)

    wallet = portfolio.get_wallet(currency_code)

    # Add to balance
    old_balance = wallet.balance
    wallet.deposit(amount)

    # Calculate estimated cost (for display)
    if currency_code == base_currency:
        cost = amount
    else:
        cost = convert_currency(amount, currency_code, base_currency, rates)

    # Save portfolio
    save_portfolio(portfolio)

    logger.info(
        f"User '{user.username}' bought {amount} {currency_code} "
        f"(balance: {old_balance} -> {wallet.balance})"
    )

    return wallet, cost


@log_action("Sell Currency")
def sell_currency(currency_code: str, amount: float) -> Tuple[Wallet, float]:
    """
    Продать валюту из портфеля.

    Args:
        currency_code: Код валюты для продажи
        amount: Сумма для продажи

    Returns:
        Кортеж (обновленный кошелек, ориентировочная стоимость в базовой валюте)

    Raises:
        NotLoggedInError: Если пользователь не вошел в систему
        ValidationError: Если входные данные недействительны
        CurrencyNotFoundError: Если валюта не поддерживается
        InsufficientFundsError: Если средств в кошельке недостаточно
        RateNotAvailableError: Если обменный курс недоступен
    """
    user, portfolio = _session.require_login()

    # Validate inputs
    currency = get_currency(currency_code)  # Validates currency exists
    currency_code = currency.code
    validate_amount(amount)

    # Get wallet
    wallet = portfolio.get_wallet(currency_code)

    # Load rates and settings
    rates = load_rates()
    settings = get_settings()
    base_currency = settings.base_currency

    # Check if currency rate exists (unless it's base currency)
    if currency_code != base_currency:
        # This will raise RateNotAvailableError if rate doesn't exist
        try:
            get_exchange_rate(currency_code, base_currency, rates)
        except RateNotAvailableError:
            raise RateNotAvailableError(
                f"Невозможно продать {currency_code}: обменный курс недоступен. "
                f"Выполните 'update-rates' для получения текущих курсов."
            )

    # Calculate estimated value (before withdrawal)
    if currency_code == base_currency:
        value = amount
    else:
        value = convert_currency(amount, currency_code, base_currency, rates)

    # Withdraw from balance
    old_balance = wallet.balance
    wallet.withdraw(amount)

    # Save portfolio
    save_portfolio(portfolio)

    logger.info(
        f"User '{user.username}' sold {amount} {currency_code} "
        f"(balance: {old_balance} -> {wallet.balance})"
    )

    return wallet, value


def _update_rates_internal() -> None:
    """
    Внутренняя функция для обновления курсов валют через parser service.

    Raises:
        ApiRequestError: Если не удалось обновить курсы
    """
    try:
        from valutatrade_hub.parser_service.config import ParserConfig
        from valutatrade_hub.parser_service.api_clients import (
            CoinGeckoClient,
            ExchangeRateApiClient,
        )
        from valutatrade_hub.parser_service.storage import RatesStorage
        from valutatrade_hub.parser_service.updater import RatesUpdater

        config = ParserConfig()
        coingecko = CoinGeckoClient(config.COINGECKO_URL, config.CRYPTO_ID_MAP)
        exchangerate = ExchangeRateApiClient(
            config.EXCHANGERATE_API_URL, config.EXCHANGERATE_API_KEY
        )
        storage = RatesStorage(config.RATES_FILE_PATH, config.HISTORY_FILE_PATH)

        updater = RatesUpdater(
            {"coingecko": coingecko, "exchangerate": exchangerate}, storage
        )
        result = updater.run_update()

        if not result["success"]:
            error_msg = f"Не удалось обновить курсы: {', '.join(result['errors'])}"
            raise ApiRequestError(error_msg)

        logger.info(f"Курсы обновлены успешно: {result['total_rates']} пар")

    except ImportError as e:
        raise ApiRequestError(f"Ошибка импорта parser service: {e}")
    except Exception as e:
        if isinstance(e, ApiRequestError):
            raise
        raise ApiRequestError(f"Неожиданная ошибка при обновлении курсов: {e}")


def _is_cache_expired(last_refresh: str, ttl_seconds: int) -> bool:
    """
    Проверить, истек ли срок действия кеша.

    Args:
        last_refresh: ISO timestamp последнего обновления
        ttl_seconds: Время жизни кеша в секундах

    Returns:
        True, если кеш устарел, False в противном случае
    """
    try:
        # Парсим timestamp (формат: "2025-10-10T15:30:00Z" или "2025-10-10T15:30:00")
        last_update = datetime.fromisoformat(last_refresh.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)

        # Проверяем, прошло ли больше времени, чем TTL
        elapsed = (now - last_update).total_seconds()
        return elapsed > ttl_seconds

    except (ValueError, AttributeError):
        # Если не удалось распарсить timestamp, считаем кеш устаревшим
        logger.warning(f"Не удалось распарсить timestamp: {last_refresh}")
        return True


def get_rate(from_currency: str, to_currency: str) -> Tuple[float, str]:
    """
    Получить обменный курс между двумя валютами.
    Автоматически обновляет курсы, если кеш устарел (TTL истек).

    Args:
        from_currency: Исходная валюта
        to_currency: Целевая валюта

    Returns:
        Кортеж (курс, отформатированная временная метка)

    Raises:
        CurrencyNotFoundError: Если валюта не поддерживается
        RateNotAvailableError: Если курс недоступен
        ApiRequestError: Если не удалось обновить курсы при необходимости
    """
    # Валидация валют через get_currency() - иначе CurrencyNotFoundError
    from_curr = get_currency(from_currency)
    to_curr = get_currency(to_currency)
    from_currency = from_curr.code
    to_currency = to_curr.code

    db = get_db()
    settings = get_settings()

    # Загружаем текущие данные курсов
    rates_data = db.load(settings.rates_file, default={})

    # Проверяем TTL и обновляем при необходимости
    ttl = settings.rates_cache_ttl
    last_refresh = rates_data.get("last_refresh")

    if (last_refresh and _is_cache_expired(last_refresh, ttl)) or not last_refresh:
        logger.info(f"Кеш курсов устарел (TTL: {ttl}s). Обновляем...")
        try:
            _update_rates_internal()
            # Перезагружаем обновленные данные
            rates_data = db.load(settings.rates_file, default={})
        except ApiRequestError as e:
            logger.error(f"Не удалось обновить курсы: {e}")
            # Продолжаем с устаревшими данными, если они есть
            if not rates_data.get("pairs"):
                raise  # Если данных вообще нет - пробрасываем ошибку
    elif not rates_data.get("pairs"):
        # Если данных нет - пытаемся обновить
        logger.info("Данные курсов отсутствуют. Обновляем...")
        _update_rates_internal()
        rates_data = db.load(settings.rates_file, default={})

    # Извлекаем курсы и timestamps из формата parser_service
    rates = {}
    rate_timestamps = {}

    pairs_data = rates_data.get("pairs", {})
    for key, value in pairs_data.items():
        if isinstance(value, dict) and "rate" in value:
            rates[key] = value["rate"]
            if "updated_at" in value:
                rate_timestamps[key] = value["updated_at"]

    # Получаем курс
    rate = get_exchange_rate(from_currency, to_currency, rates)

    # Получаем timestamp
    rate_key = f"{from_currency}_{to_currency}"
    inverse_key = f"{to_currency}_{from_currency}"

    timestamp = (
        rate_timestamps.get(rate_key)
        or rate_timestamps.get(inverse_key)
        or datetime.now().isoformat()
    )

    return rate, timestamp


def show_portfolio(base_currency: str = None) -> Dict:
    """
    Получить информацию о портфеле.

    Args:
        base_currency: Базовая валюта для расчета общей суммы (по умолчанию из настроек)

    Returns:
        Словарь с информацией о портфеле

    Raises:
        NotLoggedInError: Если пользователь не вошел в систему
    """
    user, portfolio = _session.require_login()
    settings = get_settings()

    if base_currency is None:
        base_currency = settings.base_currency
    else:
        base_currency = validate_currency_code(base_currency)

    rates = load_rates()
    wallets = portfolio.wallets

    # Calculate values
    wallet_info = []
    for code, wallet in wallets.items():
        try:
            if code == base_currency:
                value = wallet.balance
            else:
                value = convert_currency(wallet.balance, code, base_currency, rates)
        except RateNotAvailableError:
            value = 0.0

        wallet_info.append(
            {"currency": code, "balance": wallet.balance, "value_in_base": value}
        )

    total_value = sum(w["value_in_base"] for w in wallet_info)

    return {
        "username": user.username,
        "base_currency": base_currency,
        "wallets": wallet_info,
        "total_value": total_value,
    }
