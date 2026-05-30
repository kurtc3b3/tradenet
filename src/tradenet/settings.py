"""Application settings loaded from environment and .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if raw is None:
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    return int(raw)


@dataclass(frozen=True, slots=True)
class Settings:
    comtrade_subscription_key: str | None
    data_dir: Path
    http_user_agent: str
    comtrade_base_url: str
    comtrade_request_delay: float
    comtrade_max_retries: int

    def require_subscription_key(self) -> str:
        if not self.comtrade_subscription_key:
            raise ValueError(
                "UN Comtrade subscription key required. Register at "
                "https://comtradedeveloper.un.org and set COMTRADE_SUBSCRIPTION_KEY in .env"
            )
        return self.comtrade_subscription_key


@lru_cache
def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")

    data_dir_raw = _env("DATA_DIR")
    return Settings(
        comtrade_subscription_key=_env("COMTRADE_SUBSCRIPTION_KEY"),
        data_dir=Path(data_dir_raw) if data_dir_raw else PROJECT_ROOT / "data",
        http_user_agent=_env("HTTP_USER_AGENT", "tradenet/0.1") or "tradenet/0.1",
        comtrade_base_url=_env("COMTRADE_BASE_URL", "https://comtradeapi.un.org")
        or "https://comtradeapi.un.org",
        comtrade_request_delay=_env_float("COMTRADE_REQUEST_DELAY", 1.5),
        comtrade_max_retries=_env_int("COMTRADE_MAX_RETRIES", 8),
    )
