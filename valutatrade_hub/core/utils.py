
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    temporary_path.replace(path)


def load_json(path: Path, default):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        save_json(path, default)
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Файл {path.name} содержит некорректный JSON"
        ) from exc


def load_users():
    return load_json(USERS_FILE, [])


def save_users(users):
    save_json(USERS_FILE, users)


def load_portfolios():
    return load_json(PORTFOLIOS_FILE, [])


def save_portfolios(portfolios):
    save_json(PORTFOLIOS_FILE, portfolios)


def load_rates():
    rates = load_json(RATES_FILE, {
        "USD": 1.0,
        "EUR": 1.08,
        "RUB": 0.01016,
        "BTC": 59337.21,
        "ETH": 3720.0,
        "source": "local",
        "last_refresh": None,
    })

    if not isinstance(rates, dict):
        raise ValueError("Некорректный формат rates.json")

    return rates


def save_rates(rates):
    save_json(RATES_FILE, rates)
