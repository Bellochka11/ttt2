import hashlib
import hmac
import secrets

from math import isfinite
from datetime import datetime

class User:
    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ):
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self):
        return self._user_id

    @property
    def username(self):
        return self._username 

    @username.setter
    def username(self, value):
        if not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self):
        return self._hashed_password

    @property
    def salt(self):
        return self._salt

    @property
    def registration_date(self):
        return self._registration_date

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        return hashlib.sha256(
            (password + salt).encode("utf-8")
        ).hexdigest()

    @classmethod
    def create(cls, user_id: int, username: str, password: str):
        if not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        salt = secrets.token_hex(16)
        hashed_password = cls.hash_password(password, salt)

        return cls(
            user_id=user_id,
            username=username.strip(),
            hashed_password=hashed_password,
            salt=salt,
            registration_date=datetime.now(),
        )

    def verify_password(self, password: str) -> bool:
        candidate = self.hash_password(password, self._salt)
        return hmac.compare_digest(candidate, self._hashed_password)

    def change_password(self, new_password: str):
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        self._salt = secrets.token_hex(16)
        self._hashed_password = self.hash_password(
            new_password, self._salt
        )

    def get_user_info(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self._currency_code = currency_code.strip().upper()
        self.balance = balance

    @property
    def currency_code(self):
        return self._currency_code

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        if not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")

        self._balance = float(value)

    @staticmethod
    def _validate_amount(amount):
        if (not isinstance(amount, (int, float))
            or amount <= 0
        ):
            raise ValueError("'amount' должен быть положительным числом")

    def deposit(self, amount: float):
        self._validate_amount(amount)
        self.balance = self._balance + amount

    def withdraw(self, amount: float):
        self._validate_amount(amount)

        if amount > self._balance:
            raise ValueError(
                f"Недостаточно средств: доступно "
                f"{self._balance:.3f} {self._currency_code}, "
                f"требуется {amount:.3f} {self._currency_code}"
            )

        self.balance = max(0.0, self._balance - amount)

    def get_balance_info(self) -> dict:
        return {
            "currency_code": self._currency_code,
            "balance": self._balance,
        }


class Portfolio:
    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
        user: User | None = None,
    ):
        self._user_id = user_id
        self._user = user
        self._wallets = {}

        for code, wallet in (wallets or {}).items():
            self._wallets[code.upper()] = wallet

    @property
    def user(self):
        return self._user

    @property
    def user_id(self):
        return self._user_id

    @property
    def wallets(self):
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        code = currency_code.strip().upper()

        if code in self._wallets:
            raise ValueError(f"Кошелёк {code} уже существует")

        wallet = Wallet(code)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        return self._wallets.get(currency_code.upper())

    def get_total_value(
        self,
        base_currency: str = "USD",
        exchange_rates: dict | None = None,
    ) -> float:
        rates = exchange_rates or {}
        base = base_currency.upper()

        if base not in rates:
            raise ValueError(
                f"Неизвестная базовая валюта '{base}'"
            )

        base_rate = rates[base]
        total = 0.0

        for code, wallet in self._wallets.items():
            if code not in rates:
                raise ValueError(f"Нет курса для {code}")

            total += wallet.balance * rates[code] / base_rate

        return total
