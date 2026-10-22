
from datetime import datetime, timedelta
from math import isfinite

from valutatrade_hub.core.models import User, Wallet, Portfolio
from valutatrade_hub.core.utils import (
    load_users, save_users,
    load_portfolios, save_portfolios,
    load_rates, save_rates,
)


_current_user = None


def _get_rates():
    rates = load_rates()

    return {
        code: value
        for code, value in rates.items()
        if code not in ("source", "last_refresh")
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and value > 0
    }


def _rate(from_currency: str, to_currency: str) -> float:
    rates = _get_rates()
    source = from_currency.upper()
    target = to_currency.upper()

    if source not in rates or target not in rates:
        raise ValueError(
            f"Не удалось получить курс для {source}→{target}"
        )

    return rates[source] / rates[target]


def _user_from_dict(data) -> User:
    return User(
        user_id=data["user_id"],
        username=data["username"],
        hashed_password=data["hashed_password"],
        salt=data["salt"],
        registration_date=datetime.fromisoformat(
            data["registration_date"]
        ),
    )


def _user_to_dict(user: User) -> dict:
    return {
        **user.get_user_info(),
        "hashed_password": user.hashed_password,
        "salt": user.salt,
    }


def _portfolio_to_dict(portfolio: Portfolio) -> dict:
    return {
        "user_id": portfolio.user_id,
        "wallets": {
            code: wallet.get_balance_info()
            for code, wallet in portfolio.wallets.items()
        },
    }


def _portfolio_from_dict(data, user=None) -> Portfolio:
    wallets = {
        code: Wallet(
            currency_code=info.get("currency_code", code),
            balance=info["balance"],
        )
        for code, info in data.get("wallets", {}).items()
    }

    return Portfolio(data["user_id"], wallets, user)


def _save_portfolio(portfolio: Portfolio):
    portfolios = load_portfolios()
    data = _portfolio_to_dict(portfolio)

    for index, item in enumerate(portfolios):
        if item["user_id"] == portfolio.user_id:
            portfolios[index] = data
            break
    else:
        portfolios.append(data)

    save_portfolios(portfolios)


def _get_portfolio(user_id: int) -> Portfolio:
    user = next(
        (
            _user_from_dict(item)
            for item in load_users()
            if item["user_id"] == user_id
        ),
        None,
    )

    if user is None:
        raise ValueError("Пользователь не найден")

    data = next(
        (
            item for item in load_portfolios()
            if item["user_id"] == user_id
        ),
        None,
    )

    if data is None:
        portfolio = Portfolio(user_id, user=user)
        _save_portfolio(portfolio)
        return portfolio

    return _portfolio_from_dict(data, user)


def register(username: str, password: str) -> User:
    if not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")

    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users = load_users()

    if any(
        user["username"].casefold() == username.strip().casefold()
        for user in users
    ):
        raise ValueError(
            f"Такой пользователь '{username}' уже существует"
        )

    user_id = max(
        (user["user_id"] for user in users),
        default=0,
    ) + 1

    user = User.create(user_id, username, password)
    users.append(_user_to_dict(user))
    save_users(users)

    portfolios = load_portfolios()
    portfolios.append({"user_id": user_id, "wallets": {}})
    save_portfolios(portfolios)

    return user


def login(username: str, password: str) -> User:
    global _current_user

    data = next(
        (
            item for item in load_users()
            if item["username"].casefold() == username.casefold()
        ),
        None,
    )

    if data is None:
        raise ValueError(f"Пользователь '{username}' не найден")

    user = _user_from_dict(data)

    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

    _current_user = user
    return user


def logout():
    global _current_user
    _current_user = None


def get_current_user() -> User:
    if _current_user is None:
        raise ValueError("Сначала выполните login")
    return _current_user


def get_rate(from_currency: str, to_currency: str) -> dict:
    source = from_currency.upper()
    target = to_currency.upper()

    rate = _rate(source, target)
    data = load_rates()

    # Сохраняем курсы к USD в исходном формате.
    # Время здесь означает время получения локального кеша.
    timestamp = datetime.now().isoformat(timespec="seconds")
    data["source"] = data.get("source", "local")
    data["last_refresh"] = timestamp
    save_rates(data)

    return {
        "from": source,
        "to": target,
        "rate": rate,
        "updated_at": timestamp,
        "reverse_rate": 1 / rate,
    }


def show_portfolio(base_currency: str = "USD") -> dict:
    user = get_current_user()
    portfolio = _get_portfolio(user.user_id)
    rates = _get_rates()
    base = base_currency.upper()

    if base not in rates:
        raise ValueError(
            f"Неизвестная базовая валюта '{base}'"
        )

    result = []
    total = 0.0

    for code, wallet in portfolio.wallets.items():
        if code not in rates:
            raise ValueError(f"Неизвестная валюта '{code}'")

        value = wallet.balance * rates[code] / rates[base]
        total += value

        result.append({
            "currency": code,
            "balance": wallet.balance,
            "value": value,
        })

    return {
        "username": user.username,
        "base": base,
        "wallets": result,
        "total": total,
    }


def buy(currency: str, amount: float) -> dict:
    user = get_current_user()
    code = currency.upper()

    Wallet._validate_amount(amount)

    if not code or not code.isalpha():
        raise ValueError("Некорректный код валюты")

    rates = _get_rates()

    if code not in rates:
        raise ValueError(f"Не удалось получить курс для {code}→USD")

    portfolio = _get_portfolio(user.user_id)
    usd_wallet = portfolio.get_wallet("USD")
    cost = amount * _rate(code, "USD")

    if code == "USD":
        raise ValueError("Покупка USD за USD не имеет смысла")

    if usd_wallet is None:
        usd_wallet = portfolio.add_currency("USD")

    if usd_wallet.balance < cost:
        raise ValueError(
            f"Недостаточно средств: доступно "
            f"{usd_wallet.balance:.2f} USD, требуется {cost:.2f} USD"
        )

    target_wallet = portfolio.get_wallet(code)

    if target_wallet is None:
        target_wallet = portfolio.add_currency(code)

    usd_wallet.withdraw(cost)
    target_wallet.deposit(amount)

    _save_portfolio(portfolio)

    return {
        "currency": code,
        "amount": amount,
        "rate": _rate(code, "USD"),
        "cost": cost,
        "balance": target_wallet.balance,
        "usd_balance": usd_wallet.balance,
    }


def sell(currency: str, amount: float) -> dict:
    user = get_current_user()
    code = currency.upper()

    Wallet._validate_amount(amount)

    if not code or not code.isalpha():
        raise ValueError("Некорректный код валюты")

    if code == "USD":
        raise ValueError("Продажа USD за USD не имеет смысла")

    rates = _get_rates()

    if code not in rates:
        raise ValueError(f"Не удалось получить курс для {code}→USD")

    portfolio = _get_portfolio(user.user_id)
    wallet = portfolio.get_wallet(code)

    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{code}'. "
            "Он создаётся при первой покупке."
        )

    usd_wallet = portfolio.get_wallet("USD")

    if usd_wallet is None:
        usd_wallet = portfolio.add_currency("USD")

    revenue = amount * _rate(code, "USD")

    if amount > wallet.balance:
        raise ValueError(
            f"Недостаточно средств: доступно "
            f"{wallet.balance:.4f} {code}, "
            f"требуется {amount:.4f} {code}"
        )

    wallet.withdraw(amount)
    usd_wallet.deposit(revenue)

    _save_portfolio(portfolio)

    return {
        "currency": code,
        "amount": amount,
        "rate": _rate(code, "USD"),
        "revenue": revenue,
        "balance": wallet.balance,
        "usd_balance": usd_wallet.balance,
    }


def change_password(new_password: str):
    user = get_current_user()
    user.change_password(new_password)

    users = load_users()

    for index, item in enumerate(users):
        if item["user_id"] == user.user_id:
            users[index] = _user_to_dict(user)
            break

    save_users(users)


def deposit(currency: str, amount: float) -> dict:
    user = get_current_user()

    if user is None:
        raise ValueError("Сначала выполните login")

    portfolio = _get_portfolio(user.user_id)
    currency = currency.upper()

    wallet = portfolio.get_wallet(currency)

    if wallet is None:
        portfolio.add_currency(currency)
        wallet = portfolio.get_wallet(currency)

    wallet.deposit(amount)

    _save_portfolio(portfolio)  

    return {
        "currency": currency,
        "amount": amount,
        "balance": wallet.balance,
    }