"""
Модуль для роботи з локальною базою даних SQLite (aiosqlite).
Зберігає історію порушень користувачів за чатами.
"""

import aiosqlite
from datetime import datetime
from config import DB_PATH


async def init_db():
    """Створює необхідні таблиці в базі даних при запуску бота."""
    async with aiosqlite.connect(DB_PATH) as db:
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
        await db.commit()


async def record_violation(chat_id: int, user_id: int, user_name: str) -> int:
    """
    Збільшує лічильник порушень для користувача в заданому чаті та повертає нову кількість.
    """
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
