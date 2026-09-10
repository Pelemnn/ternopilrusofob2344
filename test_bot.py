"""
Комплексні тести для перевірки бази 100 пісень, MP4 медіа-генератора,
налаштування індивідуальних інтервалів чатів та автоплею.
"""

import unittest
import asyncio
import tempfile
from pathlib import Path

import config
import database
import media_engine
from songs_100 import SONGS_100, get_random_song_from_100


class Test100SongsMusicBot(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_music_bot.db"
        database.DB_PATH = self.db_path
        await database.init_db()

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    def test_songs_100_catalogue(self):
        """Перевірка, що в базі рівно 100 унікальних пісень з усіма полями."""
        self.assertEqual(len(SONGS_100), 100)
        ids = set()
        for song in SONGS_100:
            self.assertIn("id", song)
            self.assertIn("category", song)
            self.assertIn("title", song)
            self.assertIn("author", song)
            self.assertIn("chorus", song)
            self.assertNotIn(song["id"], ids, f"Duplicate song ID: {song['id']}")
            ids.add(song["id"])

        random_song = get_random_song_from_100()
        self.assertIsNotNone(random_song)
        self.assertIn(random_song["id"], range(1, 101))

    def test_media_engine_mp4_generation(self):
        """Перевірка генерації валідного MP4 відеофайлу."""
        song = SONGS_100[0]  # "Ой у лузі червона калина"
        mp4_path = media_engine.generate_song_mp4(song)
        self.assertTrue(mp4_path.exists())
        self.assertTrue(mp4_path.stat().st_size > 500)

        caption = media_engine.format_song_caption(song)
        self.assertIn("Ой у лузі червона калина", caption)
        self.assertIn("Слава Україні", caption)

    def test_time_duration_parser(self):
        """Перевірка парсингу інтервалів часу для /settings."""
        self.assertEqual(config.parse_time_duration("5m"), 5)
        self.assertEqual(config.parse_time_duration("10"), 10)
        self.assertEqual(config.parse_time_duration("15m"), 15)
        self.assertEqual(config.parse_time_duration("30m"), 30)
        self.assertEqual(config.parse_time_duration("1h"), 60)
        self.assertEqual(config.parse_time_duration("2год"), 120)
        self.assertEqual(config.parse_time_duration("1d"), 1440)

    async def test_chat_settings_and_custom_interval(self):
        """Перевірка зміни інтервалу відправки для конкретного чату."""
        chat_id = -100123456789
        chat_title = "Патріотичний чат"

        # Реєстрація (дефолтний інтервал 10 хв)
        await database.register_chat(chat_id, chat_title)
        settings = await database.get_chat_settings(chat_id)
        self.assertEqual(settings["interval_minutes"], 10)
        self.assertTrue(settings["autoplay_enabled"])

        # Зміна інтервалу на 5 хвилин через /settings 5m
        await database.set_chat_interval(chat_id, 5)
        updated_settings = await database.get_chat_settings(chat_id)
        self.assertEqual(updated_settings["interval_minutes"], 5)

        # Вимкнення та увімкнення автоплею
        await database.set_autoplay(chat_id, False)
        self.assertFalse((await database.get_chat_settings(chat_id))["autoplay_enabled"])

        await database.set_autoplay(chat_id, True)
        self.assertTrue((await database.get_chat_settings(chat_id))["autoplay_enabled"])


if __name__ == "__main__":
    unittest.main()
