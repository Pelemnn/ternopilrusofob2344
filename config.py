import os
from pathlib import Path
from dotenv import load_dotenv

# Завантаження змінних оточення з .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Шлях до бази даних SQLite
DB_PATH = BASE_DIR / "anti_rus.db"

# Драбина муту в хвилинах:
# 1-й раз: 5 хв
# 2-й раз: 15 хв
# 3-й раз: 30 хв
# 4-й раз: 60 хв (1 год)
# 5-й раз: 720 хв (12 год)
# 6-й раз: 1440 хв (24 год)
# 7-й+ раз: 2160 хв (36 год)
MUTE_LADDER = [5, 15, 30, 60, 12 * 60, 24 * 60, 36 * 60]

# Чи видаляти повідомлення з порушенням
DELETE_OFFENDING_MESSAGE = True

def get_mute_minutes(offense_count: int) -> int:
    """Повертає тривалість муту в хвилинах залежно від номера порушення."""
    if offense_count <= 0:
        return MUTE_LADDER[0]
    index = min(offense_count - 1, len(MUTE_LADDER) - 1)
    return MUTE_LADDER[index]

def get_next_mute_minutes(offense_count: int) -> int:
    """Повертає тривалість наступного покарання."""
    index = min(offense_count, len(MUTE_LADDER) - 1)
    return MUTE_LADDER[index]

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
