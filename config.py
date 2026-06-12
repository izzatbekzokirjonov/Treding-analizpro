import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    ADMIN_IDS: list = None
    FREE_LIMIT: int = 7
    PREMIUM_MONTHLY_STARS: int = 299  # Telegram Stars
    PREMIUM_MONTHLY_UZS: int = 50000  # UZS for card payment

    def __post_init__(self):
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            self.ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",")]
        else:
            self.ADMIN_IDS = []

        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not set!")
        if not self.CLAUDE_API_KEY:
            raise ValueError("CLAUDE_API_KEY not set!")


config = Config()
