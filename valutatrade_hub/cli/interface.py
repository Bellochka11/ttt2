import argparse
import shlex

# from prettytable import PrettyTable
from valutatrade_hub.core import usecases


def build_parser():
    parser = argparse.ArgumentParser(
        prog="valutatrade",
        description="Симулятор торговли валютами",
    )
    commands = parser.add_subparsers(dest="command")

    register = commands.add_parser("register")
    register.add_argument("--username", required=True)
    register.add_argument("--password", required=True)

    login = commands.add_parser("login")
    login.add_argument("--username", required=True)
    login.add_argument("--password", required=True)

    commands.add_parser("logout")

    portfolio = commands.add_parser("show-portfolio")
    portfolio.add_argument("--base", default="USD")

    buy = commands.add_parser("buy")
    buy.add_argument("--currency", required=True)
    buy.add_argument("--amount", required=True, type=float)

    sell = commands.add_parser("sell")
    sell.add_argument("--currency", required=True)
    sell.add_argument("--amount", required=True, type=float)

    rate = commands.add_parser("get-rate")
    rate.add_argument("--from", dest="from_currency", required=True)
    rate.add_argument("--to", dest="to_currency", required=True)

    deposit = commands.add_parser("deposit")
    deposit.add_argument("--currency", required=True)
    deposit.add_argument("--amount", required=True, type=float)

    commands.add_parser("help")
    commands.add_parser("exit")

    return parser


def print_help():
    print("""
Доступные команды:

  register --username alice --password 1234
  login --username alice --password 1234
  logout
  show-portfolio
  show-portfolio --base EUR
  buy --currency BTC --amount 0.05
  sell --currency BTC --amount 0.01
  get-rate --from EUR --to USD
  deposit --currency USD --amount 1000
  help
  exit
""")


def execute(args):
    if args.command == "register":
        user = usecases.register(args.username, args.password)
        print(
            f"Пользователь '{user.username}' зарегистрирован "
            f"(id={user.user_id}). Войдите: login --username "
            f"{user.username} --password ****"
        )

    elif args.command == "login":
        user = usecases.login(args.username, args.password)
        print(f"Вы вошли как '{user.username}'")

    elif args.command == "logout":
        usecases.logout()
        print("Вы вышли из системы")

    elif args.command == "show-portfolio":
        data = usecases.show_portfolio(args.base)

        print(
            f"Портфель пользователя '{data['username']}' "
            f"(база: {data['base']}):"
        )

        if not data["wallets"]:
            print("Портфель пуст")
            return

        print(f"{'Валюта':<10} {'Баланс':>18} "
          f"{'Стоимость (' + data['base'] + ')':>22}")
        for item in data["wallets"]:
            balance = f"{item['balance']:.8f}".rstrip("0").rstrip(".")
            value = f"{item['value']:.2f}"
            print(f"{item['currency']:<10} {balance:>18} {value:>22}")
        print(f"\nИТОГО: {data['total']:.2f} {data['base']}")

        # table = PrettyTable()
        # table.field_names = [
        #     "Валюта", "Баланс", f"Стоимость ({data['base']})"
        # ]

        # for item in data["wallets"]:
        #     table.add_row([
        #         item["currency"],
        #         f"{item['balance']:.8f}".rstrip("0").rstrip("."),
        #         f"{item['value']:.2f}",
        #     ])

        # print(table)
        # print(f"ИТОГО: {data['total']:.2f} {data['base']}")

    elif args.command == "buy":
        result = usecases.buy(args.currency, args.amount)
        print(
            f"Покупка выполнена: {result['amount']:.8f} "
            f"{result['currency']} по курсу "
            f"{result['rate']:.4f} USD/{result['currency']}"
        )
        print(f"Списано: {result['cost']:.2f} USD")
        print(f"Баланс {result['currency']}: {result['balance']:.8f}")
        print(f"Баланс USD: {result['usd_balance']:.2f}")

    elif args.command == "sell":
        result = usecases.sell(args.currency, args.amount)
        print(
            f"Продажа выполнена: {result['amount']:.8f} "
            f"{result['currency']} по курсу "
            f"{result['rate']:.4f} USD/{result['currency']}"
        )
        print(f"Выручка: {result['revenue']:.2f} USD")
        print(f"Остаток {result['currency']}: {result['balance']:.8f}")
        print(f"Баланс USD: {result['usd_balance']:.2f}")

    elif args.command == "get-rate":
        result = usecases.get_rate(
            args.from_currency, args.to_currency
        )
        print(
            f"Курс {result['from']}→{result['to']}: "
            f"{result['rate']:.10f}"
        )
        print(f"Обратный курс: {result['reverse_rate']:.8f}")
        print(f"Время кеша: {result['updated_at']}")
    elif args.command == "deposit":
        result = usecases.deposit(args.currency, args.amount)
        print(
            f"Кошелёк {result['currency']} пополнен "
            f"на {result['amount']:.2f}"
        )
        print(f"Новый баланс: {result['balance']:.3f}")

    elif args.command == "help":
        print_help()

    elif args.command == "exit":
        return False

    return True


def run(): # 1
    parser = build_parser()
    print("ValutaTrade Hub. Введите help для списка команд.")

    while True:
        try:
            command = input("valutatrade> ").strip()

            if not command:
                continue

            args = parser.parse_args(shlex.split(command))

            if execute(args) is False:
                print("До свидания!")
                break

        except SystemExit:
            # argparse выводит описание ошибки и завершает разбор
            # текущей команды; сам CLI продолжает работать.
            continue
        except (ValueError, KeyError, OSError) as exc:
            print(f"Ошибка: {exc}")
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break
