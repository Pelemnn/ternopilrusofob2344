"""
Модуль для роботи з локальною базою даних SQLite (aiosqlite).
Зберігає історію порушень, список адміністраторів, налаштування драбини покарань
та базу MP4 пісень через Telegram file_id.
"""

import aiosqlite
from datetime import datetime
from typing import List, Optional, Dict, Any
from config import DB_PATH, SUPER_ADMIN_ID, DEFAULT_MUTE_LADDER


async def init_db():
    """Створює необхідні таблиці в базі даних при запуску бота."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблиця порушень
        await db.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                chat_id INTEGER,
                user_id INTEGER,
                user_name TEXT,
                violation_count INTEGER DEFAULT 0,
                last_violation_at TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        
        # Таблиця призначених адміністраторів бота
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_admins (
                chat_id INTEGER,
                user_id INTEGER,
                user_name TEXT,
                added_by INTEGER,
                created_at TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            )
        """)

        # Таблиця кастомних налаштувань драбини мутів для кожного чату
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                step_1 INTEGER DEFAULT 5,
                step_2 INTEGER DEFAULT 15,
                step_3 INTEGER DEFAULT 30,
                step_4 INTEGER DEFAULT 60,
                step_5 INTEGER DEFAULT 720,
                step_6 INTEGER DEFAULT 1440,
                step_7 INTEGER DEFAULT 2160
            )
        """)

        # Таблиця завантажених MP4 пісень через file_id
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_music (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                author TEXT,
                file_id TEXT,
                file_type TEXT DEFAULT 'video',
                added_by INTEGER,
                created_at TIMESTAMP
            )
        """)
        await db.commit()


async def is_bot_admin(chat_id: int, user_id: int) -> bool:
    """Перевіряє, чи є користувач головним супер-адміном або призначеним адміном бота."""
    if user_id == SUPER_ADMIN_ID:
        return True

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM bot_admins WHERE (chat_id = ? OR chat_id = 0) AND user_id = ?",
            (chat_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def add_bot_admin(chat_id: int, user_id: int, user_name: str, added_by: int) -> bool:
    """Призначає користувача адміністратором бота."""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO bot_admins (chat_id, user_id, user_name, added_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                user_name = excluded.user_name,
                added_by = excluded.added_by,
                created_at = excluded.created_at
            """,
            (chat_id, user_id, user_name, added_by, now)
        )
        await db.commit()
    return True


async def record_violation(chat_id: int, user_id: int, user_name: str) -> int:
    """Збільшує лічильник порушень для користувача в заданому чаті та повертає нову кількість."""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT violation_count FROM violations WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            new_count = 1
            await db.execute(
                """
                INSERT INTO violations (chat_id, user_id, user_name, violation_count, last_violation_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (chat_id, user_id, user_name, new_count, now)
            )
        else:
            new_count = row[0] + 1
            await db.execute(
                """
                UPDATE violations
                SET violation_count = ?, user_name = ?, last_violation_at = ?
                WHERE chat_id = ? AND user_id = ?
                """,
                (new_count, user_name, now, chat_id, user_id)
            )
        await db.commit()
    return new_count


async def get_violation_count(chat_id: int, user_id: int) -> int:
    """Повертає поточну кількість порушень користувача."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT violation_count FROM violations WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def reset_violations(chat_id: int, user_id: int) -> bool:
    """Скидає лічильник порушень для користувача."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM violations WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        await db.commit()
    return True


async def get_top_violators(chat_id: int, limit: int = 10) -> list[dict]:
    """Повертає топ порушників чату."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT user_id, user_name, violation_count, last_violation_at
            FROM violations
            WHERE chat_id = ?
            ORDER BY violation_count DESC
            LIMIT ?
            """,
            (chat_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "user_id": r[0],
                    "user_name": r[1],
                    "violation_count": r[2],
                    "last_violation_at": r[3]
                }
                for r in rows
            ]


async def get_chat_mute_ladder(chat_id: int) -> List[int]:
    """Отримує кастомну драбину покарань для чату або повертає дефолтну."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT step_1, step_2, step_3, step_4, step_5, step_6, step_7
            FROM chat_settings WHERE chat_id = ?
            """,
            (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return list(row)
    return list(DEFAULT_MUTE_LADDER)


async def set_chat_mute_step(chat_id: int, step_num: int, minutes: int) -> bool:
    """Встановлює кастомну тривалість муту для кроку (1..7)."""
    if step_num < 1 or step_num > 7 or minutes <= 0:
        return False

    column_name = f"step_{step_num}"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO chat_settings (chat_id, step_1, step_2, step_3, step_4, step_5, step_6, step_7)
            VALUES (?, 5, 15, 30, 60, 720, 1440, 2160)
            ON CONFLICT(chat_id) DO NOTHING
            """,
            (chat_id,)
        )
        await db.execute(
            f"UPDATE chat_settings SET {column_name} = ? WHERE chat_id = ?",
            (minutes, chat_id)
        )
        await db.commit()
    return True


async def add_custom_music(title: str, author: str, file_id: str, file_type: str, added_by: int) -> int:
    """Зберігає file_id MP4 відео/аудіо треку в базі даних."""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO custom_music (title, author, file_id, file_type, added_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, author, file_id, file_type, added_by, now)
        )
        await db.commit()
        return cursor.lastrowid


async def get_all_custom_music() -> List[Dict[str, Any]]:
    """Повертає список усіх збережених треків із file_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, title, author, file_id, file_type FROM custom_music ORDER BY id DESC"
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
