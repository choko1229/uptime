import json
import secrets
from pathlib import Path
from urllib.parse import quote_plus

DATA_DIR = Path("data")
SECRET_KEY_PATH = DATA_DIR / "secret_key"
DATABASE_CONFIG_PATH = DATA_DIR / "database.json"

_REQUIRED_DATABASE_KEYS = ("host", "port", "name", "user", "password")


def get_or_create_secret_key() -> str:
    if SECRET_KEY_PATH.exists():
        value = SECRET_KEY_PATH.read_text(encoding="utf-8").strip()
        if value:
            return value

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    value = secrets.token_urlsafe(48)
    SECRET_KEY_PATH.write_text(value, encoding="utf-8")
    return value


def load_database_config() -> dict | None:
    if not DATABASE_CONFIG_PATH.exists():
        return None
    data = json.loads(DATABASE_CONFIG_PATH.read_text(encoding="utf-8"))
    if not all(key in data for key in _REQUIRED_DATABASE_KEYS):
        return None
    return data


def save_database_config(config: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_CONFIG_PATH.write_text(json.dumps(config), encoding="utf-8")


def build_database_url(config: dict, *, driver: str = "mysql+aiomysql") -> str:
    user = quote_plus(str(config["user"]))
    password = quote_plus(str(config["password"]))
    return (
        f"{driver}://{user}:{password}"
        f"@{config['host']}:{int(config['port'])}/{config['name']}"
    )
