"""Environment-based configuration; imports never require a token."""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def database_url() -> str:
    return os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT / 'db.sqlite3'}")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_chat_id: int

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("Set BOT_TOKEN before starting the bot")
        try:
            admin_chat_id = int(os.environ["ADMIN_CHAT_ID"])
        except (KeyError, ValueError) as exc:
            raise ValueError("Set ADMIN_CHAT_ID to a non-zero Telegram chat ID") from exc
        if not admin_chat_id:
            raise ValueError("ADMIN_CHAT_ID must not be zero")
        return cls(token, admin_chat_id)
