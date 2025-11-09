"""Интерфейс командной строки для ValutaTrade Hub."""

import shlex
from typing import List

from prettytable import PrettyTable

from valutatrade_hub.core import usecases
from valutatrade_hub.core.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    AuthenticationError,
    NotLoggedInError,
    InsufficientFundsError,
    RateNotAvailableError,
    ValidationError,
    WalletNotFoundError,
    CurrencyNotFoundError,
    ApiRequestError,
)
from valutatrade_hub.infra.database import get_db
from valutatrade_hub.infra.settings import get_settings
from valutatrade_hub.logging_config import setup_logging, get_logger
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
# Import parser service modules
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = get_logger("cli")


class CLI:
    """Обработчик интерфейса командной строки."""

    def __init__(self):
        """Инициализация CLI."""
        self.running = True
        self.commands = {
            "register": self.cmd_register,
            "login": self.cmd_login,
            "logout": self.cmd_logout,
            "show-portfolio": self.cmd_show_portfolio,
            "buy": self.cmd_buy,
            "sell": self.cmd_sell,
            "get-rate": self.cmd_get_rate,
            "update-rates": self.cmd_update_rates,
            "show-rates": self.cmd_show_rates,
            "help": self.cmd_help,
            "exit": self.cmd_exit,
            "quit": self.cmd_exit,
        }

    def parse_args(self, tokens: List[str]) -> dict:
        """
        Парсинг аргументов команды в формате --key value.

        Args:
            tokens: Список токенов команды

        Returns:
            Словарь распарсенных аргументов
        """
        args = {}
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith("--"):
                key = token[2:]  # Remove --
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                    args[key] = tokens[i + 1]
                    i += 2
                else:
                    args[key] = True
                    i += 1
            else:
                i += 1
        return args

    def cmd_register(self, args: dict) -> None:
        """Регистрация нового пользователя."""
        username = args.get("username")
        password = args.get("password")

        if not username or not password:
            print("Ошибка: требуются параметры --username и --password")
            print("Использование: register --username <имя> --password <пароль>")
            return

        try:
            user = usecases.register_user(username, password)
            print(f"\nПользователь '{username}' успешно зарегистрирован (id={user.user_id})")
            print(f"Войдите в систему: login --username {username} --password ****\n")
        except UserAlreadyExistsError as e:
            print(f"Ошибка: {e}")
        except ValidationError as e:
            print(f"Ошибка валидации: {e}")

    def cmd_login(self, args: dict) -> None:
        """Вход пользователя в систему."""
        username = args.get("username")
        password = args.get("password")

        if not username or not password:
            print("Ошибка: требуются параметры --username и --password")
            print("Использование: login --username <имя> --password <пароль>")
            return

        try:
            user, _ = usecases.login_user(username, password)
            print(f"\nДобро пожаловать, {username}!")
            print("Вы вошли в систему.\n")
        except UserNotFoundError as e:
            print(f"Ошибка: {e}")
        except AuthenticationError as e:
            print(f"Ошибка: {e}")

    def cmd_logout(self, args: dict) -> None:
        """Выход текущего пользователя."""
        session = usecases.get_session()
        if not session.is_logged_in():
            print("В данный момент никто не вошел в систему.")
            return

        username = session.current_user.username
        usecases.logout_user()
        print(f"Пользователь '{username}' вышел из системы.")

    def cmd_show_portfolio(self, args: dict) -> None:
        """Отображение портфеля пользователя."""
        try:
            base_currency = args.get("base", None)
            portfolio_info = usecases.show_portfolio(base_currency)

            print(
                f"\nПортфель пользователя '{portfolio_info['username']}' (базовая валюта: {portfolio_info['base_currency']})"
            )
            print("-" * 70)

            if not portfolio_info["wallets"]:
                print("Кошельки отсутствуют. Используйте команду 'buy' для добавления валют.")
            else:
                table = PrettyTable()
                table.field_names = [
                    "Валюта",
                    "Баланс",
                    f"Стоимость ({portfolio_info['base_currency']})",
                ]
                table.align["Баланс"] = "r"
                table.align[f"Стоимость ({portfolio_info['base_currency']})"] = "r"

                for wallet in portfolio_info["wallets"]:
                    table.add_row(
                        [
                            wallet["currency"],
                            f"{wallet['balance']:.4f}",
                            f"{wallet['value_in_base']:.2f}",
                        ]
                    )

                print(table)
                print("-" * 70)
                print(
                    f"ИТОГО: {portfolio_info['total_value']:,.2f} {portfolio_info['base_currency']}\n"
                )

        except NotLoggedInError as e:
            print(f"Ошибка: {e}")
        except ValidationError as e:
            print(f"Ошибка валидации: {e}")

    def cmd_buy(self, args: dict) -> None:
        """Покупка валюты."""
        currency = args.get("currency")
        amount_str = args.get("amount")

        if not currency or not amount_str:
            print("Ошибка: требуются параметры --currency и --amount")
            print("Использование: buy --currency <КОД> --amount <число>")
            return

        try:
            amount = float(amount_str)
        except ValueError:
            print("Ошибка: сумма должна быть числом")
            return

        try:
            wallet, cost = usecases.buy_currency(currency, amount)

            # Получаем курс для отображения
            settings = get_settings()
            base = settings.base_currency

            if currency != base:
                try:
                    rate, _ = usecases.get_rate(currency, base)
                    print(
                        f"\nПокупка завершена: {amount:.4f} {currency} по курсу {rate:.2f} {base}/{currency}"
                    )
                except RateNotAvailableError:
                    print(f"\nПокупка завершена: {amount:.4f} {currency}")
            else:
                print(f"\nПокупка завершена: {amount:.4f} {currency}")

            print(f"Баланс кошелька: {wallet.balance:.4f} {currency}")
            if cost > 0:
                print(f"Ориентировочная стоимость: {cost:,.2f} {base}\n")

        except NotLoggedInError as e:
            print(f"Ошибка: {e}")
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            print("Используйте 'help get-rate' для просмотра поддерживаемых валют")
        except ValidationError as e:
            print(f"Ошибка валидации: {e}")
        except RateNotAvailableError as e:
            print(f"Ошибка: {e}")

    def cmd_sell(self, args: dict) -> None:
        """Продажа валюты."""
        currency = args.get("currency")
        amount_str = args.get("amount")

        if not currency or not amount_str:
            print("Ошибка: требуются параметры --currency и --amount")
            print("Использование: sell --currency <КОД> --amount <число>")
            return

        try:
            amount = float(amount_str)
        except ValueError:
            print("Ошибка: сумма должна быть числом")
            return

        try:
            wallet, value = usecases.sell_currency(currency, amount)

            # Получаем курс для отображения
            settings = get_settings()
            base = settings.base_currency

            if currency != base:
                try:
                    rate, _ = usecases.get_rate(currency, base)
                    print(
                        f"\nПродажа завершена: {amount:.4f} {currency} по курсу {rate:.2f} {base}/{currency}"
                    )
                except RateNotAvailableError:
                    print(f"\nПродажа завершена: {amount:.4f} {currency}")
            else:
                print(f"\nПродажа завершена: {amount:.4f} {currency}")

            print(f"Баланс кошелька: {wallet.balance:.4f} {currency}")
            if value > 0:
                print(f"Ориентировочная стоимость: {value:,.2f} {base}\n")

        except NotLoggedInError as e:
            print(f"Ошибка: {e}")
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            print("Используйте 'help get-rate' для просмотра поддерживаемых валют")
        except ValidationError as e:
            print(f"Ошибка валидации: {e}")
        except InsufficientFundsError as e:
            print(f"Ошибка: {e}")
        except WalletNotFoundError as e:
            print(f"Ошибка: {e}")
        except RateNotAvailableError as e:
            print(f"Ошибка: {e}")

    def cmd_get_rate(self, args: dict) -> None:
        """Получение обменного курса между двумя валютами."""
        from_currency = args.get("from")
        to_currency = args.get("to")

        if not from_currency or not to_currency:
            print("Ошибка: требуются параметры --from и --to")
            print("Использование: get-rate --from <КОД> --to <КОД>")
            return

        try:
            rate, timestamp = usecases.get_rate(from_currency, to_currency)
            print("\nОбменный курс:")
            print(f"1 {from_currency.upper()} = {rate:.4f} {to_currency.upper()}")
            print(f"Обновлено: {timestamp}\n")
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            print("Используйте 'help get-rate' для просмотра поддерживаемых валют")
        except RateNotAvailableError as e:
            print(f"Ошибка: {e}")
        except ApiRequestError as e:
            print(f"Ошибка: {e}")
            print("Повторите попытку позже или проверьте подключение к сети")

    def cmd_update_rates(self, args: dict) -> None:
        """Обновление обменных курсов через Parser Service."""
        source_filter = args.get("source")

        print("\nИНФО: Начинается обновление курсов...")
        if source_filter:
            print(f"ИНФО: Фильтр по источнику: {source_filter}")

        try:
            # Инициализация конфигурации
            config = ParserConfig()

            # Валидация конфигурации
            if not config.validate():
                print(
                    "\nВНИМАНИЕ: EXCHANGERATE_API_KEY не установлен. Будут доступны только курсы криптовалют."
                )

            # Инициализация API клиентов
            coingecko_client = CoinGeckoClient(
                base_url=config.COINGECKO_URL,
                crypto_id_map=config.CRYPTO_ID_MAP,
                vs_currency=config.BASE_CURRENCY,
                api_key=config.COINGECKO_API_KEY,
                timeout=config.REQUEST_TIMEOUT,
            )

            exchangerate_client = ExchangeRateApiClient(
                base_url=config.EXCHANGERATE_API_URL,
                api_key=config.EXCHANGERATE_API_KEY,
                base_currency=config.BASE_CURRENCY,
                fiat_currencies=config.FIAT_CURRENCIES,
                timeout=config.REQUEST_TIMEOUT,
            )

            clients = {
                "coingecko": coingecko_client,
                "exchangerate": exchangerate_client,
            }

            # Инициализация хранилища и updater
            storage = RatesStorage(
                rates_file_path=config.RATES_FILE_PATH,
                history_file_path=config.HISTORY_FILE_PATH,
            )

            updater = RatesUpdater(clients=clients, storage=storage)

            # Запуск обновления
            result = updater.run_update(source_filter=source_filter)

            # Отображение результатов
            if result["success"]:
                print(
                    f"\nОбновление успешно. Всего курсов обновлено: {result['total_rates']}"
                )
                print(f"Последнее обновление: {result['timestamp']}")

                if result["rates_by_source"]:
                    print("\nКурсы по источникам:")
                    for source, count in result["rates_by_source"].items():
                        print(f"  {source}: {count} курсов")
                print()
            else:
                print("\nОбновление завершено с ошибками.")
                print(f"Всего курсов обновлено: {result['total_rates']}")

                if result["errors"]:
                    print("\nОшибки:")
                    for error in result["errors"]:
                        print(f"  {error}")
                print("\nПроверьте logs/valutatrade.log для деталей.\n")

        except Exception as e:
            logger.exception("Error updating exchange rates")
            print(f"\nОШИБКА: Не удалось обновить курсы - {e}")
            print("Проверьте logs/valutatrade.log для деталей.\n")

    def cmd_show_rates(self, args: dict) -> None:
        """Отображение всех доступных обменных курсов из кэша."""
        currency_filter = args.get("currency")
        top = args.get("top")

        try:
            # Инициализация конфигурации и хранилища
            config = ParserConfig()
            storage = RatesStorage(
                rates_file_path=config.RATES_FILE_PATH,
                history_file_path=config.HISTORY_FILE_PATH,
            )

            # Загрузка кэша
            rates_data = storage.load_rates_cache()

            if not rates_data:
                print("\nЛокальный кэш пуст. Выполните 'update-rates' для получения данных.\n")
                return

            pairs = rates_data.get("pairs", {})
            last_refresh = rates_data.get("last_refresh", "N/A")

            if not pairs:
                print("\nКурсы в кэше не найдены. Выполните 'update-rates' для получения данных.\n")
                return

            print(
                f"\nКурсы из кэша (обновлено {last_refresh[:19] if len(last_refresh) > 19 else last_refresh}):"
            )
            print("-" * 70)

            # Фильтрация курсов если указана валюта
            if currency_filter:
                currency_filter = currency_filter.upper()
                filtered_pairs = {
                    k: v for k, v in pairs.items() if currency_filter in k
                }

                if not filtered_pairs:
                    print(f"Курс для '{currency_filter}' не найден в кэше.\n")
                    return

                pairs = filtered_pairs

            # Построение таблицы
            table = PrettyTable()
            table.field_names = ["Валютная пара", "Курс", "Источник", "Обновлено"]
            table.align["Курс"] = "r"

            # Сортировка пар
            sorted_pairs = sorted(pairs.items())

            # Применение фильтра top для крипто если указан
            if top:
                try:
                    top_n = int(top)
                    # Фильтр для криптопар (BTC, ETH, SOL) и сортировка по курсу
                    crypto_pairs = [
                        (k, v)
                        for k, v in sorted_pairs
                        if any(k.startswith(c) for c in ["BTC", "ETH", "SOL"])
                    ]
                    crypto_pairs.sort(key=lambda x: x[1]["rate"], reverse=True)
                    sorted_pairs = crypto_pairs[:top_n]
                except ValueError:
                    print(f"Предупреждение: Неверное значение --top '{top}', показываем все курсы")

            for pair_key, pair_data in sorted_pairs:
                rate = pair_data.get("rate", 0)
                source = pair_data.get("source", "Неизвестно")
                timestamp = pair_data.get("updated_at", "N/A")

                # Форматирование валютной пары
                if "_" in pair_key:
                    from_curr, to_curr = pair_key.split("_", 1)
                    pair_display = f"{from_curr} → {to_curr}"
                else:
                    pair_display = pair_key

                # Усечение временной метки
                timestamp_display = timestamp[:19] if len(timestamp) > 19 else timestamp

                table.add_row([pair_display, f"{rate:.4f}", source, timestamp_display])

            print(table)
            print("-" * 70)

            # Отображение сводки
            summary = rates_data.get("summary", {})
            total_pairs = summary.get("total_pairs", len(pairs))
            print(f"Всего курсов показано: {len(sorted_pairs)} / {total_pairs}")

            if summary.get("rates_by_source"):
                print("\nКурсы по источникам:")
                for source, count in summary["rates_by_source"].items():
                    print(f"  - {source}: {count}")

            print()

        except Exception as e:
            logger.exception("Error displaying rates")
            print(f"\nОшибка: Не удалось отобразить курсы - {e}\n")

    def cmd_help(self, args: dict) -> None:
        """Отображение справочной информации."""
        help_text = """
ValutaTrade Hub - Платформа симуляции валютной торговли

Доступные команды:

register --username <имя> --password <пароль>
    Регистрация нового пользователя

login --username <имя> --password <пароль>
    Вход в систему

logout
    Выход из системы

show-portfolio [--base <ВАЛЮТА>]
    Отображение портфеля (базовая валюта по умолчанию: USD)

buy --currency <КОД> --amount <число>
    Покупка валюты и добавление в портфель

sell --currency <КОД> --amount <число>
    Продажа валюты из портфеля

get-rate --from <КОД> --to <КОД>
    Получение обменного курса между двумя валютами

update-rates
    Обновление обменных курсов из CoinGecko API

show-rates
    Отображение всех доступных обменных курсов

help
    Показать эту справку

exit / quit
    Выход из приложения

Примеры:

> update-rates
> show-rates
> register --username alice --password 1234
> login --username alice --password 1234
> buy --currency BTC --amount 0.05
> show-portfolio
> get-rate --from BTC --to USD
> sell --currency BTC --amount 0.01
> logout
"""
        print(help_text)

        # Отображение поддерживаемых валют
        from valutatrade_hub.core.currencies import get_supported_currencies

        currencies = get_supported_currencies()
        fiat = [c for c in currencies if c in ["USD", "EUR", "RUB", "GBP", "JPY", "CNY", "KRW"]]
        crypto = [c for c in currencies if c in ["BTC", "ETH", "SOL"]]

        print("Поддерживаемые валюты:")
        print(f"  Фиатные: {', '.join(fiat)}")
        print(f"  Криптовалюты: {', '.join(crypto)}")
        print()

    def cmd_exit(self, args: dict) -> None:
        """Выход из приложения."""
        session = usecases.get_session()
        if session.is_logged_in():
            print(f"Выход из системы {session.current_user.username}...")
            usecases.logout_user()
        print("До свидания!")
        self.running = False

    def process_command(self, command_line: str) -> None:
        """
        Обработка введенной команды.

        Args:
            command_line: Строка с командой
        """
        if not command_line.strip():
            return

        try:
            # Парсинг команды с помощью shlex для правильной обработки кавычек
            tokens = shlex.split(command_line)
        except ValueError as e:
            print(f"Ошибка при разборе команды: {e}")
            return

        if not tokens:
            return

        cmd_name = tokens[0].lower()
        args = self.parse_args(tokens[1:])

        if cmd_name in self.commands:
            try:
                self.commands[cmd_name](args)
            except Exception as e:
                logger.exception(f"Unexpected error in command '{cmd_name}'")
                print(f"Неожиданная ошибка: {e}")
                print("Проверьте логи для получения дополнительной информации.")
        else:
            print(f"Неизвестная команда: {cmd_name}")
            print("Введите 'help' для списка доступных команд.")

    def run(self) -> None:
        """Запуск основного цикла CLI."""
        print("\nValutaTrade Hub - Платформа симуляции валютной торговли")
        print("Введите 'help' для списка команд или 'exit' для выхода.\n")

        while self.running:
            try:
                # Отображение приглашения с текущим пользователем
                session = usecases.get_session()
                if session.is_logged_in():
                    prompt = f"{session.current_user.username}> "
                else:
                    prompt = "> "

                command_line = input(prompt)
                self.process_command(command_line)

            except KeyboardInterrupt:
                print("\nИспользуйте 'exit' или 'quit' для выхода.")
            except EOFError:
                print("\nДо свидания!")
                break


def main():
    """Главная точка входа для CLI приложения."""
    # Настройка логирования
    setup_logging()
    logger.info("ValutaTrade Hub starting...")

    # Инициализация файлов базы данных
    db = get_db()
    settings = get_settings()

    db.initialize_file(settings.users_file, [])
    db.initialize_file(settings.portfolios_file, [])


    # Запуск CLI
    cli = CLI()
    # Инициализация файла курсов с дефолтными значениями если не существует
    cli.cmd_update_rates({})

    cli.run()

    logger.info("ValutaTrade Hub shutting down")


if __name__ == "__main__":
    main()
