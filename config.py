import os
import re
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Завантаження змінних оточення з .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Головний Супер-Адміністратор бота
SUPER_ADMIN_ID = 998913975

# Шлях до бази даних SQLite
DB_PATH = BASE_DIR / "anti_rus.db"

# Стандартна драбина муту в хвилинах (за замовчуванням):
# 1-й: 5 хв
# 2-й: 15 хв
# 3-й: 30 хв
# 4-й: 60 хв (1 год)
# 5-й: 720 хв (12 год)
# 6-й: 1440 хв (24 год)
# 7-й+: 2160 хв (36 год)
DEFAULT_MUTE_LADDER = [5, 15, 30, 60, 12 * 60, 24 * 60, 36 * 60]

# Чи видаляти повідомлення з порушенням
DELETE_OFFENDING_MESSAGE = True


def parse_time_duration(time_str: str) -> Optional[int]:
    """
    Парсить рядок часу (наприклад '10m', '30', '2h', '1d', '36h') у хвилини.
    
    Підтримувані суфікси:
    - m / хв / хвилини -> хвилини
    - h / год / години -> години (* 60)
    - d / д / дні / доба -> дні (* 1440)
    """
    if not time_str:
        return None
    time_str = time_str.strip().lower()

    # Якщо просто число без суфікса — вважаємо хвилинами
    if time_str.isdigit():
        val = int(time_str)
        return val if val > 0 else None

    # Пошук за регулярним виразом
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


def get_mute_minutes(offense_count: int, ladder: Optional[List[int]] = None) -> int:
    """Повертає тривалість муту в хвилинах залежно від номера порушення."""
    current_ladder = ladder or DEFAULT_MUTE_LADDER
    if offense_count <= 0:
        return current_ladder[0]
    index = min(offense_count - 1, len(current_ladder) - 1)
    return current_ladder[index]


def get_next_mute_minutes(offense_count: int, ladder: Optional[List[int]] = None) -> int:
    """Повертає тривалість наступного покарання."""
    current_ladder = ladder or DEFAULT_MUTE_LADDER
    index = min(offense_count, len(current_ladder) - 1)
    return current_ladder[index]


def format_duration_ukr(minutes: int) -> str:
    """Форматує тривалість у зручний людиночитаний український вигляд."""
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
    elif hours == 36 and rem_min == 0:
        return "36 годин (1.5 доби)"
    elif rem_min == 0:
        return f"{hours} годин"
    else:
        return f"{hours} год. {rem_min} хв."
