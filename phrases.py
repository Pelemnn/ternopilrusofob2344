"""
Модуль патріотичних фраз, жартів та шаблонів сповіщень про мут.
"""

import random
from config import format_duration_ukr, get_next_mute_minutes
from curses import get_ukrainian_curse_advice

# Патріотичні слогани, підколки та антиросійські приколи
PATRIOTIC_PUNCHLINES = [
    "🇺🇦 <b>Путін — Хуйло!</b> Не говоріть ворожою мовою в українському чаті!",
    "🇺🇦 <b>Рускій воєнний корабль — іді нахуй!</b> А ти помовчи і повчи українську.",
    "🇺🇦 <b>Бавовнятко плаче</b> щоразу, коли хтось пише мовою окупанта.",
    "🇺🇦 <b>Щелепа заклинила?</b> Тримай перепочинок, щоб розім'яти язика для солов'їної!",
    "🇺🇦 <b>Тут вам не Тамбов!</b> У цьому чаті діє закон солов'їної мови.",
    "🇺🇦 <b>СБУ вже зацікавилось</b> твоїм словниковим запасом. Відпочинь у муті!",
    "🇺🇦 <b>Доброго вечора, ми з України!</b> А звідки ти з такими словами?",
    "🇺🇦 <b>Пакет потрібен?</b> Бо російські слова в цьому чаті утилізуються миттєво!",
    "🇺🇦 <b>Конотопські відьми</b> наклали закляття мовчання за використання московитської!",
    "🇺🇦 <b>Не ганьби рідний край!</b> Солов'їна мова — найкраща у світі.",
    "🇺🇦 <b>Червона калина схилилася</b> від такої кількості російщини. Виправляйся!",
    "🇺🇦 <b>Без паніки, працює ППО!</b> Російське слово успішно перехоплено і збито.",
    "🇺🇦 <b>Паляниця, полуниця, укрзалізниця!</b> Повторюй це, поки сидиш у муті."
]


def get_random_punchline() -> str:
    """Повертає випадковий патріотичний панчлайн."""
    return random.choice(PATRIOTIC_PUNCHLINES)


def build_mute_message(
    user_mention: str,
    offense_count: int,
    current_mute_minutes: int,
    detected_reason: str,
    detected_sample: str
) -> str:
    """
    Формує інформативне та дотепне повідомлення про покарання,
    включаючи заміну російських матів на українські відповідники.
    """
    punchline = get_random_punchline()
    current_duration_str = format_duration_ukr(current_mute_minutes)
    
    next_mute_minutes = get_next_mute_minutes(offense_count)
    next_duration_str = format_duration_ukr(next_mute_minutes)

    # Перевіряємо чи є колоритна українська заміна для лайки
    curse_tip = get_ukrainian_curse_advice(detected_sample)
    curse_tip_block = f"\n💡 <i>{curse_tip}</i>\n" if curse_tip else ""

    msg = (
        f"{punchline}\n\n"
        f"👤 <b>Порушник:</b> {user_mention}\n"
        f"🔍 <b>Причина:</b> {detected_reason} (<code>{detected_sample}</code>)\n"
        f"{curse_tip_block}"
        f"🔢 <b>Номер порушення:</b> {offense_count}\n"
        f"⏳ <b>Вирок:</b> Мут на <b>{current_duration_str}</b>\n\n"
        f"⚠️ <i>Увага: якщо напишеш російською ще раз — отримаєш мут вже на <b>{next_duration_str}</b>!</i>"
    )
    return msg


def build_unmute_admin_message(user_mention: str) -> str:
    """Повідомлення, коли адмін знімає покарання."""
    return f"🕊️ Користувача {user_mention} помилувано. Спілкуйтеся українською!"
