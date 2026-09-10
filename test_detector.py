"""
Комплексні тести для перевірки детектора мови, матів, одруківок, бази даних та конфігурації покарань.
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

        # Перевірка інтеграції в повідомлення про мут
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

    def test_mute_ladder_durations(self):
        """Тест розрахунку тривалості муту."""
        self.assertEqual(config.get_mute_minutes(1), 5)
        self.assertEqual(config.format_duration_ukr(config.get_mute_minutes(1)), "5 хвилин")

        self.assertEqual(config.get_mute_minutes(2), 15)
        self.assertEqual(config.format_duration_ukr(config.get_mute_minutes(2)), "15 хвилин")

        self.assertEqual(config.get_mute_minutes(3), 30)
        self.assertEqual(config.format_duration_ukr(config.get_mute_minutes(3)), "30 хвилин")

        self.assertEqual(config.get_mute_minutes(4), 60)
        self.assertEqual(config.format_duration_ukr(config.get_mute_minutes(4)), "1 годину")

        self.assertEqual(config.get_mute_minutes(5), 720)
        self.assertEqual(config.format_duration_ukr(config.get_mute_minutes(5)), "12 годин")

        self.assertEqual(config.get_mute_minutes(6), 1440)
        self.assertEqual(config.format_duration_ukr(config.get_mute_minutes(6)), "24 години (1 добу)")

        self.assertEqual(config.get_mute_minutes(7), 2160)
        self.assertEqual(config.format_duration_ukr(config.get_mute_minutes(7)), "36 годин (1.5 доби)")

        self.assertEqual(config.get_mute_minutes(10), 2160)


class TestDatabase(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        """Створюємо тимчасову базу даних для ізольованого тесту."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_anti_rus.db"
        database.DB_PATH = self.db_path
        await database.init_db()

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_violation_flow(self):
        chat_id = -100123456789
        user_id = 999888777
        user_name = "@test_user"

        count = await database.get_violation_count(chat_id, user_id)
        self.assertEqual(count, 0)

        c1 = await database.record_violation(chat_id, user_id, user_name)
        self.assertEqual(c1, 1)

        c2 = await database.record_violation(chat_id, user_id, user_name)
        self.assertEqual(c2, 2)

        count = await database.get_violation_count(chat_id, user_id)
        self.assertEqual(count, 2)

        top = await database.get_top_violators(chat_id, limit=5)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]["user_id"], user_id)
        self.assertEqual(top[0]["violation_count"], 2)

        await database.reset_violations(chat_id, user_id)
        count_after = await database.get_violation_count(chat_id, user_id)
        self.assertEqual(count_after, 0)


if __name__ == "__main__":
    unittest.main()
