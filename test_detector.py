"""
Комплексні тести для перевірки детектора мови, матів, одруківок,
бази даних, адмін-прав, налаштувань часу та 30 пісень УПА.
"""

import unittest
import asyncio
import os
import tempfile
from pathlib import Path

import config
import database
import curses
import phrases
import music_data
from detector import detect_russian


class TestRussianDetector(unittest.TestCase):

    def test_russian_letters(self):
        """Тест виявлення специфічних російських літер."""
        cases = [
            ("Привет, как дела? Мы были на рыбалке", True, "ы"),
            ("Это просто тест", True, "э"),
            ("Ёлка стоит в комнате", True, "ё"),
            ("Объявление на стене", True, "ъ"),
            ("СЫР", True, "ы"),
            ("Эй, послушай!", True, "э"),
            ("Під'їзд і объявление", True, "ъ"),
        ]
        for text, expected, expected_char in cases:
            with self.subTest(text=text):
                is_rus, reason, sample = detect_russian(text)
                self.assertEqual(is_rus, expected, f"Failed on text: {text}")
                self.assertIn(expected_char.lower(), reason.lower())

    def test_russian_words_with_common_alphabet(self):
        """Тест виявлення суто російських слів, написаних спільними літерами (без ы, ё, ъ, э)."""
        cases = [
            ("Подай мне полотенце пожалуйста", "полотенце"),
            ("Привет всем участникам чата", "привет"),
            ("Большое спасибо за помощь", "спасибо"),
            ("Почему ты так думаешь?", "почему"),
            ("Вчера мы купили сахар", "вчера"),
            ("Какая красивая машина", "красивая"),
            ("Мне очень нравится этот фильм", "нравится"),
            ("Все делается вовремя", "делается"),
            ("Зачем ты это сказал?", "зачем"),
            ("Я сейчас приду", "сейчас"),
            ("Сегодня хорошая погода", "сегодня"),
            ("Это вообще кошмар", "вообще"),
            ("Давай пойдем вместе", "давай"),
            ("Ладно, договорились", "ладно"),
            ("Здесь живут говорящие птицы", "говорящие"),
        ]
        for text, sample_hint in cases:
            with self.subTest(text=text):
                is_rus, reason, sample = detect_russian(text)
                self.assertTrue(is_rus, f"Should detect Russian in: '{text}', got ({is_rus}, {reason}, {sample})")

    def test_russian_typos_and_leetspeak(self):
        """Тест на виявлення одруківок та завуальованих слів (блч, бл@ть, првет тощо)."""
        cases = [
            ("блч що це таке", "блч"),
            ("ну блч", "блч"),
            ("бл@ть ти серйозно", "блять"),
            ("првет друже", "првет"),
            ("полотнце впало", "полотнце"),
            ("ну ти і $ука", "сука"),
            ("п0шел н@хуй відсіля", "пошел"),
            ("пішов нахуй звідси", "пішов нахуй"),
            ("пздц яка ситуація", "пздц"),
        ]
        for text, sample_hint in cases:
            with self.subTest(text=text):
                is_rus, reason, sample = detect_russian(text)
                self.assertTrue(is_rus, f"Should detect typo/curse in: '{text}', got ({is_rus}, {reason}, {sample})")

    def test_curse_words_ukrainian_advice(self):
        """Тест отримання порад щодо заміни російських матів на українські відповідники."""
        curse_cases = ["блять", "бля", "блч", "нахуй", "пошел нахуй", "сука", "пиздец", "ебать", "хуйня"]
        for curse in curse_cases:
            advice = curses.get_ukrainian_curse_advice(curse)
            self.assertIsNotNone(advice, f"Should generate advice for '{curse}'")
            self.assertIn("Не кажи", advice)

        msg = phrases.build_mute_message(
            user_mention="@test",
            offense_count=1,
            current_mute_minutes=5,
            detected_reason="виявлено російську лайку",
            detected_sample="блять"
        )
        self.assertIn("Не кажи", msg)

    def test_ukrainian_text_no_false_positives(self):
        """Тест на те, що чиста українська мова НЕ визначається як російська."""
        ukrainian_texts = [
            "Привіт усім! Як ваші справи?",
            "Подай, будь ласка, рушник і цукор.",
            "Дякую за допомогу, друже!",
            "Слава Україні! Героям слава!",
            "Сьогодні гарна погода у Києві.",
            "Ми прямуємо до перемоги.",
            "Будь ласка, зачиніть двері.",
            "Я читаю українську книжку.",
            "Хлопці та дівчата зібралися на площі.",
            "Кохайтеся, чорнобриві, та не з москалями.",
            "Паляниця зі свіжим медом смакує чудово.",
            "Усе буде Україна!",
            "Скільки годин залишилося до зустрічі?",
            "Я знаю відповідь на це питання.",
            "Ми любимо рідну Україну.",
            "Слухаємо гарну музику.",
            "Правда завжди перемагає.",
            "Вода в річці чиста та прозора.",
            "Трясця тобі в печінку!",
            "Йди до сраки, москалю поганий!",
            "Курва, яка чудова вишиванка!",
        ]
        for text in ukrainian_texts:
            with self.subTest(text=text):
                is_rus, reason, sample = detect_russian(text)
                self.assertFalse(
                    is_rus,
                    f"False positive on Ukrainian text: '{text}'. Reason: {reason}, Sample: {sample}"
                )

    def test_time_duration_parser(self):
        """Тест парсера часу для команди /mute та /settings."""
        self.assertEqual(config.parse_time_duration("15m"), 15)
        self.assertEqual(config.parse_time_duration("30"), 30)
        self.assertEqual(config.parse_time_duration("1h"), 60)
        self.assertEqual(config.parse_time_duration("2год"), 120)
        self.assertEqual(config.parse_time_duration("1d"), 1440)
        self.assertEqual(config.parse_time_duration("36h"), 2160)
        self.assertEqual(config.parse_time_duration("3доба"), 4320)

    def test_upa_songs_collection(self):
        """Тест наявності 30 патріотичних пісень УПА."""
        self.assertEqual(len(music_data.UPA_SONGS), 30)
        for song in music_data.UPA_SONGS:
            self.assertTrue(song.get("title"))
            self.assertTrue(song.get("author"))
            self.assertTrue(song.get("chorus"))
            self.assertTrue(song.get("link"))


class TestDatabase(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        """Створюємо тимчасову базу даних для ізольованого тесту."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_anti_rus.db"
        database.DB_PATH = self.db_path
        await database.init_db()

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_admin_and_settings_flow(self):
        chat_id = -100123456789
        super_admin_id = config.SUPER_ADMIN_ID
        bot_admin_id = 1122334455

        # Перевірка супер-адміна
        self.assertTrue(await database.is_bot_admin(chat_id, super_admin_id))

        # Додавання нового адміна через /setfob
        self.assertFalse(await database.is_bot_admin(chat_id, bot_admin_id))
        await database.add_bot_admin(chat_id, bot_admin_id, "@moderator", super_admin_id)
        self.assertTrue(await database.is_bot_admin(chat_id, bot_admin_id))

        # Перевірка дефолтної драбини
        ladder = await database.get_chat_mute_ladder(chat_id)
        self.assertEqual(ladder[0], 5)

        # Кастомне налаштування кроку 1 на 36 годин (2160 хв) через /settings
        await database.set_chat_mute_step(chat_id, 1, 2160)
        new_ladder = await database.get_chat_mute_ladder(chat_id)
        self.assertEqual(new_ladder[0], 2160)
        self.assertEqual(config.get_mute_minutes(1, new_ladder), 2160)


if __name__ == "__main__":
    unittest.main()
