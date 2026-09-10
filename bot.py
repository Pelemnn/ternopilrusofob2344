"""
Головний файл запуску Telegram-бота «Анти-Русифікатор».
"""

import sys
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command
from aiogram.types import ChatPermissions
from aiogram.exceptions import TelegramBadRequest

import config
import database
import detector
import phrases

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("anti_rus_bot")


dp = Dispatcher()


def get_user_display_name(user: types.User) -> str:
    """Формує зручне ім'я користувача або посилання на нього."""
    if user.username:
        return f"@{user.username}"
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    return full_name or f"ID:{user.id}"


def get_user_mention_html(user: types.User) -> str:
    """Створює HTML-посилання на профіль користувача."""
    name = (user.first_name or "Користувач").replace("<", "&lt;").replace(">", "&gt;")
    return f'<a href="tg://user?id={user.id}">{name}</a>'


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обробник команди /start."""
    text = (
        "👋 <b>Привіт! Я бот «Анти-Русифікатор».</b>\n\n"
        "Моя місія — оберігати українські Telegram-чати від російської мови та московитських слів.\n\n"
        "<b>Як мене використовувати:</b>\n"
        "1. Додайте мене у вашу групу або супергрупу.\n"
        "2. Надайте мені <b>права адміністратора</b> (обов'язково: <i>блокування/обмеження учасників</i> та <i>видалення повідомлень</i>).\n"
        "3. Я автоматично буду слідкувати за кожним повідомленням!\n\n"
        "<b>Драбина покарань:</b>\n"
        "• 1-ше порушення: 5 хв\n"
        "• 2-ге порушення: 15 хв\n"
        "• 3-тє порушення: 30 хв\n"
        "• 4-те порушення: 1 год\n"
        "• 5-те порушення: 12 год\n"
        "• 6-те порушення: 24 год\n"
        "• 7-ме+ порушення: 36 год\n\n"
        "🇺🇦 <i>Слава Україні! Героям Слава!</i>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обробник команди /help."""
    text = (
        "📋 <b>Команди бота:</b>\n\n"
        "/start — Інформація про бота\n"
        "/help — Список доступних команд\n"
        "/my_punishments — Перевірити свою кількість порушень\n"
        "/top — Топ любителів московитської мови в чаті\n"
        "/unmute (відповіддю на повідомлення) — Зняти мут з користувача (тільки для адмінів)\n"
        "/reset (відповіддю на повідомлення) — Скинути лічильник покарань (тільки для адмінів)\n"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("my_punishments"))
async def cmd_my_punishments(message: types.Message):
    """Показує кількість порушень того, хто викликав команду."""
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Ця команда доступна лише в групах.")
        return

    user_id = message.from_user.id
    count = await database.get_violation_count(message.chat.id, user_id)
    mention = get_user_mention_html(message.from_user)

    if count == 0:
        await message.answer(
            f"✨ {mention}, у вас <b>0 порушень</b>! Дякуємо, що спілкуєтеся солов'їною! 🇺🇦",
            parse_mode=ParseMode.HTML
        )
    else:
        next_duration = config.format_duration_ukr(config.get_next_mute_minutes(count))
        await message.answer(
            f"⚠️ {mention}, у вас зафіксовано <b>{count}</b> порушень.\n"
            f"Наступне порушення призведе до муту на <b>{next_duration}</b>!",
            parse_mode=ParseMode.HTML
        )


@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    """Показує топ порушників у чаті."""
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Ця команда доступна лише в групах.")
        return

    top_list = await database.get_top_violators(message.chat.id, limit=10)
    if not top_list:
        await message.answer("🏆 У цьому чаті ще ніхто не порушував правила! Усі спілкуються українською!")
        return

    text_lines = ["🏆 <b>Топ порушників чату за кількістю російських слів:</b>\n"]
    for i, item in enumerate(top_list, 1):
        uname = (item['user_name'] or f"ID:{item['user_id']}").replace("<", "&lt;").replace(">", "&gt;")
        text_lines.append(f"{i}. <b>{uname}</b> — {item['violation_count']} порушень")

    await message.answer("\n".join(text_lines), parse_mode=ParseMode.HTML)


@dp.message(Command("unmute"))
async def cmd_unmute(message: types.Message, bot: Bot):
    """Зняття муту адміном."""
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    # Перевірка чи автор команди є адміном
    member = await message.chat.get_member(message.from_user.id)
    if member.status not in ("creator", "administrator"):
        await message.reply("❌ Ця команда доступна тільки адміністраторам чату.")
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("ℹ️ Відповідайте цією командою на повідомлення користувача, якого хочете розмутити.")
        return

    target_user = message.reply_to_message.from_user
    try:
        # Повертаємо базові дозволи
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            permissions=permissions
        )
        target_mention = get_user_mention_html(target_user)
        await message.answer(phrases.build_unmute_admin_message(target_mention), parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Помилка при unmute: {e}")
        await message.reply(f"❌ Не вдалося розмутити користувача: {e}")


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    """Скидання лічильника порушень адміном."""
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    member = await message.chat.get_member(message.from_user.id)
    if member.status not in ("creator", "administrator"):
        await message.reply("❌ Ця команда доступна тільки адміністраторам чату.")
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("ℹ️ Відповідайте цією командою на повідомлення користувача, якому хочете скинути лічильник.")
        return

    target_user = message.reply_to_message.from_user
    await database.reset_violations(message.chat.id, target_user.id)
    target_mention = get_user_mention_html(target_user)
    await message.answer(
        f"✅ Лічильник покарань для {target_mention} успішно скинуто до 0.",
        parse_mode=ParseMode.HTML
    )


@dp.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_group_message(message: types.Message, bot: Bot):
    """
    Основний обробник текстових повідомлень у групах.
    Перевіряє текст на наявність російських літер та слів.
    """
    # Ігноруємо повідомлення від інших ботів та системні
    if not message.from_user or message.from_user.is_bot:
        return

    # Отримуємо текст повідомлення або підпис до фото/відео/документа
    text = message.text or message.caption
    if not text:
        return

    # Виконуємо детекцію російської мови
    is_rus, reason, sample = detector.detect_russian(text)
    if not is_rus:
        return

    user = message.from_user
    user_name = get_user_display_name(user)
    user_mention = get_user_mention_html(user)

    logger.info(
        f"Виявлено російську в чаті {message.chat.id} від {user_name} ({user.id}): "
        f"{reason} ('{sample}') | Текст: {text[:50]}"
    )

    # Фіксуємо порушення в БД
    offense_count = await database.record_violation(message.chat.id, user.id, user_name)
    mute_minutes = config.get_mute_minutes(offense_count)
    until_date = datetime.now() + timedelta(minutes=mute_minutes)

    # Перевіряємо статус користувача в чаті (адмінів Telegram забороняє обмежувати звичайним ботам)
    is_admin = False
    try:
        chat_member = await message.chat.get_member(user.id)
        if chat_member.status in ("creator", "administrator"):
            is_admin = True
    except Exception as e:
        logger.warning(f"Не вдалося перевірити статус користувача: {e}")

    # Спроба видалити повідомлення з порушенням
    if config.DELETE_OFFENDING_MESSAGE:
        try:
            await message.delete()
        except TelegramBadRequest as e:
            logger.warning(f"Не вдалося видалити повідомлення: {e}")

    # Застосовуємо мут (якщо це не адмін)
    if not is_admin:
        try:
            await bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            logger.info(f"Користувача {user.id} замучено на {mute_minutes} хв.")
        except TelegramBadRequest as e:
            logger.error(f"Помилка при спробі замутити користувача {user.id}: {e}")
    else:
        logger.info(f"Користувач {user.id} є адміністратором. Мут пропущено.")

    # Формуємо та надсилаємо попереджувальне повідомлення
    mute_text = phrases.build_mute_message(
        user_mention=user_mention,
        offense_count=offense_count,
        current_mute_minutes=mute_minutes,
        detected_reason=reason or "російська мова",
        detected_sample=sample or ""
    )

    if is_admin:
        mute_text += "\n\n<i>(P.S. Ви адміністратор, тому мут не застосовано, але майте совість!)</i>"

    await message.answer(mute_text, parse_mode=ParseMode.HTML)


from aiohttp import web

async def handle_health_check(request):
    return web.Response(text="Анти-Русифікатор Telegram Bot is running! 🇺🇦", content_type="text/plain")


async def start_web_server(port: int):
    """Запускає легкий HTTP сервер для проходження health check на Render.com"""
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"HTTP health-check сервер успішно запущено на порту {port} (для Render.com)")


async def main():
    """Точка входу в програму."""
    if not config.BOT_TOKEN:
        logger.critical(
            "ПОМИЛКА: Не вказано BOT_TOKEN!\n"
            "Створіть файл .env або додайте змінну оточення BOT_TOKEN у налаштуваннях Render."
        )
        sys.exit(1)

    # Ініціалізація бази даних
    await database.init_db()
    logger.info("База даних SQLite успішно ініціалізована.")

    # Якщо запущено на Render.com (наявна змінна PORT) — запускаємо healthcheck сервер
    import os
    port_env = os.getenv("PORT")
    if port_env:
        try:
            port = int(port_env)
            await start_web_server(port)
        except Exception as e:
            logger.warning(f"Не вдалося запустити health-check сервер на порту {port_env}: {e}")

    bot = Bot(token=config.BOT_TOKEN)
    logger.info("Запуск бота «Анти-Русифікатор»...")

    try:
        # Скидаємо старі оновлення і починаємо опитування
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

