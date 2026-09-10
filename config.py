import os
import re
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Головний Супер-Адміністратор бота
SUPER_ADMIN_ID = 998913975

# Шлях до бази даних SQLite
DB_PATH = BASE_DIR / "music_bot.db"

# Папка для локальних MP4 файлів
MUSIC_DIR = BASE_DIR / "music"

# Інтервал автоматичної відправки пісень за замовчуванням (10 хвилин)
DEFAULT_AUTO_PLAY_INTERVAL = 10


def parse_time_duration(time_str: str) -> Optional[int]:
    """
    Парсить рядок часу (наприклад '5m', '10', '15m', '1h', '2h', '3d') у хвилини.
    """
    if not time_str:
        return None
    time_str = time_str.strip().lower()

    if time_str.isdigit():
        val = int(time_str)
        return val if val > 0 else None

    match = re.match(r"^(\d+)\s*([a-zA-Zа-яА-ЯёЁіІїЇєЄґҐ]+)?$", time_str)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2) or "m"

    if unit in ("m", "min", "хв", "хвилин", "хвилини", "хвилина", "м"):
        return amount
    elif unit in ("h", "hr", "hour", "год", "годин", "години", "година", "г"):
        return amount * 60
    elif unit in ("d", "day", "days", "д", "днів", "дні", "день", "доба", "доби"):
        return amount * 1440
    else:
        return amount


def format_duration_ukr(minutes: int) -> str:
    """Форматує тривалість у зручний людиночитаний вигляд українською."""
    if minutes < 60:
        if minutes in (1, 21, 31, 41, 51):
            return f"{minutes} хвилину"
        elif minutes in (2, 3, 4, 22, 23, 24, 32, 33, 34, 42, 43, 44, 52, 53, 54):
            return f"{minutes} хвилини"
        else:
            return f"{minutes} хвилин"

    hours = minutes // 60
    rem_min = minutes % 60

    if hours == 1 and rem_min == 0:
        return "1 годину"
    elif hours in (2, 3, 4) and rem_min == 0:
        return f"{hours} години"
    elif hours == 24 and rem_min == 0:
        return "24 години (1 добу)"
    elif rem_min == 0:
        return f"{hours} годин"
    else:
        return f"{hours} год. {rem_min} хв."
