import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from src.models import ConfigError, SourceConfig

logger = logging.getLogger(__name__)

REQUIRED_KEYS = [
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_BOT_TOKEN",
    "ADMIN_CHAT_ID",
    "OPENROUTER_API_KEY",
    "BINANCE_SQUARE_API_KEY",
    "TELEGRAM_CHANNEL_ID",
    "SYSTEM_MODE",
]

BOT_TOKEN_PATTERN = re.compile(r"\d+:[\w-]+")


class Config:
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        bot_token: str,
        admin_chat_id: str,
        openrouter_api_key: str,
        binance_square_api_key: str,
        telegram_channel_id: str,
        system_mode: str,
        sources: list[SourceConfig],
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.admin_chat_id = admin_chat_id
        self.openrouter_api_key = openrouter_api_key
        self.binance_square_api_key = binance_square_api_key
        self.telegram_channel_id = telegram_channel_id
        self.system_mode = system_mode
        self.sources = sources


def _warn_defaults(values: dict[str, str]) -> None:
    for key, val in values.items():
        if "your_" in val.lower():
            logger.warning(
                "Default placeholder detected in %s — value contains 'your_'. Update .env with real credentials.",
                key,
            )


def _validate(values: dict[str, str]) -> None:
    for key in REQUIRED_KEYS:
        if key not in values or not values[key].strip():
            raise ConfigError(f"Missing required config key: {key}")

    api_id_raw = values["TELEGRAM_API_ID"]
    if not api_id_raw.strip().isdigit():
        raise ConfigError(f"TELEGRAM_API_ID must be numeric, got: {api_id_raw}")

    api_hash = values["TELEGRAM_API_HASH"]
    if len(api_hash) != 32:
        raise ConfigError(
            f"TELEGRAM_API_HASH must be exactly 32 characters, got {len(api_hash)}"
        )

    bot_token = values["TELEGRAM_BOT_TOKEN"]
    if not BOT_TOKEN_PATTERN.fullmatch(bot_token):
        raise ConfigError(f"TELEGRAM_BOT_TOKEN does not match expected format")


def _load_sources() -> list[SourceConfig]:
    active_path = Path("sources.json")
    default_path = Path("sources.default.json")

    if not active_path.exists():
        if default_path.exists():
            import shutil
            shutil.copy(str(default_path), str(active_path))
            logger.info("Copied sources.default.json → sources.json")
        else:
            logger.warning("No sources.default.json found; proceeding with empty source list")
            return []

    try:
        with open(active_path, encoding="utf-8") as f:
            data = json.load(f)
        return [SourceConfig.model_validate(item) for item in data]
    except (json.JSONDecodeError, Exception) as e:
        raise ConfigError(f"Failed to load sources.json: {e}") from e


def load_config() -> Config:
    env_path = Path(".env")
    if not env_path.exists():
        raise ConfigError(
            ".env file not found. Copy .env.example to .env and fill in your credentials."
        )

    load_dotenv(env_path)

    values = {key: os.getenv(key, "") for key in REQUIRED_KEYS}
    _validate(values)
    _warn_defaults(values)

    sources = _load_sources()

    return Config(
        api_id=int(values["TELEGRAM_API_ID"]),
        api_hash=values["TELEGRAM_API_HASH"],
        bot_token=values["TELEGRAM_BOT_TOKEN"],
        admin_chat_id=values["ADMIN_CHAT_ID"],
        openrouter_api_key=values["OPENROUTER_API_KEY"],
        binance_square_api_key=values["BINANCE_SQUARE_API_KEY"],
        telegram_channel_id=values["TELEGRAM_CHANNEL_ID"],
        system_mode=values["SYSTEM_MODE"],
        sources=sources,
    )
