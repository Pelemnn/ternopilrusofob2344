"""
Модуль для роботи з базою даних SQLite (aiosqlite).
Підтримує індивідуальні налаштування інтервалу відправки для кожного чату,
статус автоплею та збереження MP4 треків.
"""

import random
import aiosqlite
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from config import DB_PATH, DEFAULT_AUTO_PLAY_INTERVAL


async def init_db():
    """Створює необхідні таблиці в базі даних при запуску бота."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблиця чатів з індивідуальним інтервалом відправки
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT,
                autoplay_enabled BOOLEAN DEFAULT 1,
                interval_minutes INTEGER DEFAULT 10,
                last_sent_at TIMESTAMP,
                added_at TIMESTAMP
            )
        """)

        # Таблиця збережених MP4 пісень через Telegram file_id
        await db.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                author TEXT,
                file_id TEXT UNIQUE,
                file_type TEXT DEFAULT 'video',
                added_by INTEGER,
                created_at TIMESTAMP
            )
        """)
        await db.commit()


async def register_chat(chat_id: int, chat_title: str):
    """Реєструє чат із базовим інтервалом у 10 хвилин."""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO chats (chat_id, chat_title, autoplay_enabled, interval_minutes, last_sent_at, added_at)
            VALUES (?, ?, 1, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                chat_title = excluded.chat_title
            """,
            (chat_id, chat_title, DEFAULT_AUTO_PLAY_INTERVAL, now, now)
        )
        await db.commit()


async def get_chat_settings(chat_id: int) -> Dict[str, Any]:
    """Повертає налаштування автоплею та інтервалу для чату."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT autoplay_enabled, interval_minutes, last_sent_at FROM chats WHERE chat_id = ?",
            (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "autoplay_enabled": bool(row[0]),
                    "interval_minutes": row[1] or DEFAULT_AUTO_PLAY_INTERVAL,
                    "last_sent_at": row[2]
                }
    return {
        "autoplay_enabled": True,
        "interval_minutes": DEFAULT_AUTO_PLAY_INTERVAL,
        "last_sent_at": None
    }


async def set_chat_interval(chat_id: int, minutes: int) -> bool:
    """Встановлює кастомний інтервал відправки пісень у хвилинах для чату."""
    if minutes <= 0:
        return False
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO chats (chat_id, chat_title, autoplay_enabled, interval_minutes, last_sent_at, added_at)
            VALUES (?, 'Chat', 1, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                interval_minutes = excluded.interval_minutes
            """,
            (chat_id, minutes, now, now)
        )
        await db.commit()
    return True


async def set_autoplay(chat_id: int, enabled: bool):
    """Вмикає або вимикає авто-відправку для чату."""
    val = 1 if enabled else 0
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO chats (chat_id, chat_title, autoplay_enabled, interval_minutes, last_sent_at, added_at)
            VALUES (?, 'Chat', ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET autoplay_enabled = ?
            """,
            (chat_id, val, DEFAULT_AUTO_PLAY_INTERVAL, now, now, val)
        )
        await db.commit()


async def get_due_chats() -> List[int]:
    """
    Повертає список ID чатів, для яких настав час надіслати наступну MP4 пісню
    згідно з їхнім індивідуальним інтервалом.
    """
    now = datetime.now()
    due_chats = []

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT chat_id, interval_minutes, last_sent_at FROM chats WHERE autoplay_enabled = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                chat_id = r[0]
                interval_min = r[1] or DEFAULT_AUTO_PLAY_INTERVAL
                last_sent_str = r[2]

                if not last_sent_str:
                    due_chats.append(chat_id)
                    continue

                try:
                    last_sent_dt = datetime.fromisoformat(last_sent_str)
                    if now - last_sent_dt >= timedelta(minutes=interval_min):
                        due_chats.append(chat_id)
                except Exception:
                    due_chats.append(chat_id)

    return due_chats


async def update_chat_last_sent(chat_id: int):
    """Оновлює час останньої відправки пісні для чату."""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE chats SET last_sent_at = ? WHERE chat_id = ?",
            (now, chat_id)
        )
        await db.commit()


async def add_song(title: str, author: str, file_id: str, file_type: str, added_by: int) -> int:
    """Додає нову MP4 пісню в базу даних."""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO songs (title, author, file_id, file_type, added_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_id) DO UPDATE SET
                title = excluded.title,
                author = excluded.author
            """,
            (title, author, file_id, file_type, added_by, now)
        )
        await db.commit()
        return cursor.lastrowid


async def get_all_songs() -> List[Dict[str, Any]]:
    """Повертає список усіх збережених MP4 пісень."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, title, author, file_id, file_type FROM songs ORDER BY id ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "title": r[1],
                    "author": r[2],
                    "file_id": r[3],
                    "file_type": r[4]
                }
                for r in rows
            ]


async def get_random_song() -> Optional[Dict[str, Any]]:
    """Повертає випадкову MP4 пісню з бази даних."""
    songs = await get_all_songs()
    if not songs:
        return None
    return random.choice(songs)


async def delete_song(song_id: int) -> bool:
    """Видаляє пісню за ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        await db.commit()
        return cursor.rowcount > 0
