"""
Головний файл запуску Telegram-бота «Патріотична Музика УПА».
Завантажує та надсилає реальні MP4 відео за прямими посиланнями конкретних авторів:
1. Автоматично з налаштовуваним інтервалом (за замовчуванням кожні 10 хв).
2. За командою /music (або /song, /play) у будь-який момент.
3. Налаштування інтервалу таймера через /settings [час].
4. Додавання власних відео/аудіо через /addmusic.
5. Працює 24/7 на Render.com з вбудованим HTTP health check сервером.
"""

import sys
import os
import random
import asyncio
import logging
from pathlib import Path

from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramConflictError

import config
import database
import media_engine
from songs_100 import SONGS_100, get_random_song_from_100

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("music_bot")

dp = Dispatcher()


async def check_admin_rights(message: types.Message) -> bool:
    """Перевіряє, чи є користувач супер-адміном (998913975) або адміном чату."""
    if message.from_user.id == config.SUPER_ADMIN_ID:
        return True
    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("creator", "administrator"):
            return True
    except Exception:
        pass
    return False


async def send_random_song(bot: Bot, chat_id: int) -> bool:
    """
    Завантажує MP4 відео за прямим посиланням автора та надсилає його в чат.
    """
    # 1. Перевіряємо кастомні завантажені треки через file_id
    custom_song = await database.get_random_song()
    if custom_song and random.random() < 0.25:
        caption = (
            f"🎬 <b>{custom_song['title']}</b>\n"
            f"👤 <i>{custom_song['author']}</i>\n\n"
            f"🇺🇦 <i>Слава Україні! Героям Слава!</i>"
        )
        try:
            if custom_song['file_type'] == "video":
                await bot.send_video(chat_id=chat_id, video=custom_song['file_id'], caption=caption, parse_mode=ParseMode.HTML, supports_streaming=True)
            else:
                await bot.send_audio(chat_id=chat_id, audio=custom_song['file_id'], caption=caption, parse_mode=ParseMode.HTML)
            return True
        except Exception as e:
            logger.warning(f"Помилка відправки custom file_id: {e}")

    # 2. Вибираємо випадкову пісню зі 100 історичних пісень
    song = get_random_song_from_100()

    # Завантажуємо MP4 відео у фоновому потоці
    video_path = await asyncio.to_thread(media_engine.download_mp4_video, song)
    caption = media_engine.format_song_caption(song)

    try:
        if video_path and video_path.exists():
            video_file = FSInputFile(video_path)
            await bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
                supports_streaming=True
            )
        else:
            # Якщо завантаження недоступне — відправляємо структуроване повідомлення
            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False
            )
        return True
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.warning(f"Не вдалося надіслати відео у чат {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Помилка при надсиланні пісні: {e}")
        return False


async def auto_play_worker(bot: Bot):
    """
    Фоновий процес: перевіряє чати кожні 20 секунд і надсилає MP4 відео,
    якщо настав час згідно з індивідуальним інтервалом кожного чату.
    """
    logger.info("Фоновий таймер авто-відправки MP4 пісень запущено.")
    while True:
        try:
            await asyncio.sleep(20)
            due_chats = await database.get_due_chats()
            for chat_id in due_chats:
                success = await send_random_song(bot, chat_id)
                if success:
                    await database.update_chat_last_sent(chat_id)
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Помилка у auto_play_worker: {e}")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Запуск бота та реєстрація чату для автоплею."""
    chat_title = message.chat.title or message.from_user.full_name or "Chat"
    await database.register_chat(message.chat.id, chat_title)

    text = (
        "🇺🇦 <b>Привіт! Я бот «Патріотична Музика УПА».</b>\n\n"
        "У моїй базі зібрано <b>100 автентичних історичних пісень</b> (ОУН-УПА 1940-х, Січові Стрільці 1914–1920, Козацькі думи).\n\n"
        "Я <b>завантажую та надсилаю виключно MP4 відео</b> за прямими посиланнями авторів:\n"
        "• ⏰ <b>Автоматично за таймером</b> (за замовчуванням кожні 10 хв)!\n"
        "• 🎬 За командою <code>/music</code> у будь-який момент!\n\n"
        "<b>Команди:</b>\n"
        "• /music або /song — Отримати випадкове MP4 відео зараз\n"
        "• /settings [час] — Налаштувати таймер авто-відправки (наприклад: <code>/settings 5m</code>, <code>/settings 15m</code>, <code>/settings 1h</code>)\n"
        "• /list — Список 100 пісень у базі\n"
        "• /autoplay on|off — Увімкнути/вимкнути автоплей у чаті\n"
        "• /addmusic [назва] — Додати власне відео/аудіо (для адміна)\n\n"
        "🇺🇦 <i>Слава Україні! Героям Слава!</i>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обробник команди /help."""
    text = (
        "📋 <b>Список команд бота:</b>\n\n"
        "🎬 <b>Музичні MP4 відео:</b>\n"
        "• /music або /song — Надіслати випадкове MP4 відео з автором і приспівом\n"
        "• /list — Переглянути каталог 100 історичних пісень\n\n"
        "⚙️ <b>Налаштування автоплею:</b>\n"
        "• <code>/settings</code> — Переглянути поточний інтервал відправки\n"
        "• <code>/settings [час]</code> — Встановити свій інтервал (наприклад: <code>/settings 5m</code>, <code>/settings 15m</code>, <code>/settings 30m</code>, <code>/settings 1h</code>)\n"
        "• <code>/autoplay on</code> або <code>/autoplay off</code> — Увімкнути/вимкнути автоплей\n\n"
        "👮‍♂️ <b>Для адміністраторів:</b>\n"
        "• <code>/addmusic [назва]</code> (відповіддю на відео/аудіо або з файлом) — Додати в базу\n"
        "• <code>/delmusic [ID]</code> — Видалити пісню за номером\n"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("music", "song", "play"))
async def cmd_music(message: types.Message, bot: Bot):
    """Миттєва відправка випадкового MP4 відео зі 100 шедеврів."""
    chat_title = message.chat.title or message.from_user.full_name or "Chat"
    await database.register_chat(message.chat.id, chat_title)

    await send_random_song(bot, message.chat.id)


@dp.message(Command("settings"))
async def cmd_settings(message: types.Message, command: CommandObject):
    """Налаштування інтервалу авто-відправки пісень у чаті."""
    is_admin = await check_admin_rights(message)
    if not is_admin and message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.reply("⚠️ Тільки адміністратори чату можуть змінювати налаштування таймера.")
        return

    chat_id = message.chat.id
    current_chat = await database.get_chat_settings(chat_id)
    if not current_chat:
        chat_title = message.chat.title or message.from_user.full_name or "Chat"
        await database.register_chat(chat_id, chat_title)
        current_chat = await database.get_chat_settings(chat_id)

    arg = command.args.strip() if command.args else ""
    if not arg:
        current_mins = current_chat["interval_minutes"]
        time_text = config.format_duration(current_mins)
        status_text = "🟢 Увімкнено" if current_chat["autoplay_enabled"] else "🔴 Вимкнено"

        text = (
            f"⚙️ <b>Поточні налаштування автоплею:</b>\n\n"
            f"• ⏱️ Інтервал відправки: <b>кожні {time_text}</b>\n"
            f"• 📡 Статус автоплею: <b>{status_text}</b>\n\n"
            f"Щоб змінити інтервал, напишіть:\n"
            f"👉 <code>/settings 5m</code> (кожні 5 хв)\n"
            f"👉 <code>/settings 15m</code> (кожні 15 хв)\n"
            f"👉 <code>/settings 30m</code> (кожні 30 хв)\n"
            f"👉 <code>/settings 1h</code> (щогодини)\n"
            f"👉 <code>/settings 2h</code> (кожні 2 години)"
        )
        await message.answer(text, parse_mode=ParseMode.HTML)
        return

    new_minutes = config.parse_duration(arg)
    if new_minutes is None:
        await message.reply(
            "⚠️ Невірний формат часу!\n"
            "Приклади: <code>/settings 5m</code>, <code>/settings 15m</code>, <code>/settings 1h</code>, <code>/settings 2h30m</code>."
        )
        return

    await database.update_chat_interval(chat_id, new_minutes)
    formatted_time = config.format_duration(new_minutes)
    await message.answer(
        f"✅ <b>Інтервал успішно змінено!</b>\n"
        f"Тепер MP4 відео будуть надсилатися <b>кожні {formatted_time}</b>.",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("autoplay"))
async def cmd_autoplay(message: types.Message, command: CommandObject):
    """Увімкнення або вимкнення автоматичної відправки пісень."""
    is_admin = await check_admin_rights(message)
    if not is_admin and message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.reply("⚠️ Тільки адміністратори чату можуть змінювати статус автоплею.")
        return

    arg = (command.args or "").strip().lower()
    chat_id = message.chat.id

    if arg in ("on", "1", "true", "так", "увімк"):
        await database.set_chat_autoplay(chat_id, True)
        await message.reply("🟢 <b>Автоплей увімкнено!</b> MP4 пісні надсилатимуться за графіком.", parse_mode=ParseMode.HTML)
    elif arg in ("off", "0", "false", "ні", "вимк"):
        await database.set_chat_autoplay(chat_id, False)
        await message.reply("🔴 <b>Автоплей вимкнено.</b> Пісні надсилатимуться тільки за командою /music.", parse_mode=ParseMode.HTML)
    else:
        chat_data = await database.get_chat_settings(chat_id)
        current = "🟢 Увімкнено" if (chat_data and chat_data["autoplay_enabled"]) else "🔴 Вимкнено"
        await message.reply(
            f"Статус автоплею: <b>{current}</b>\n\n"
            f"Використання:\n"
            f"• <code>/autoplay on</code> — увімкнути\n"
            f"• <code>/autoplay off</code> — вимкнути",
            parse_mode=ParseMode.HTML
        )


@dp.message(Command("list"))
async def cmd_list(message: types.Message, command: CommandObject):
    """Показує список пісень посторінково."""
    page = 1
    if command.args and command.args.strip().isdigit():
        page = max(1, int(command.args.strip()))

    per_page = 10
    total_pages = (len(SONGS_100) + per_page - 1) // per_page
    page = min(page, total_pages)

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    current_songs = SONGS_100[start_idx:end_idx]

    lines = [f"📚 <b>Каталог історичних пісень (Сторінка {page}/{total_pages}):</b>\n"]
    for s in current_songs:
        lines.append(f"<b>#{s['id']:03d}</b> {s['title']} — <i>{s['author']}</i> ({s['category']})")

    lines.append(f"\n👉 Щоб відкрити іншу сторінку, введіть: <code>/list 2</code> (від 1 до {total_pages})")
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)


@dp.message(Command("addmusic"))
async def cmd_addmusic(message: types.Message, command: CommandObject):
    """Додавання власної пісні у базу даних бота (відео або аудіо)."""
    is_admin = await check_admin_rights(message)
    if not is_admin:
        await message.reply("⚠️ Ця команда доступна лише для супер-адміна.")
        return

    title = command.args.strip() if command.args else "Патріотичний трек"
    author = message.from_user.full_name or "Користувач"

    target_msg = message.reply_to_message if message.reply_to_message else message

    file_id = None
    file_type = "audio"

    if target_msg.video:
        file_id = target_msg.video.file_id
        file_type = "video"
    elif target_msg.audio:
        file_id = target_msg.audio.file_id
        file_type = "audio"
    elif target_msg.document and target_msg.document.mime_type and target_msg.document.mime_type.startswith("video/"):
        file_id = target_msg.document.file_id
        file_type = "video"
    elif target_msg.document and target_msg.document.mime_type and target_msg.document.mime_type.startswith("audio/"):
        file_id = target_msg.document.file_id
        file_type = "audio"

    if not file_id:
        await message.reply(
            "⚠️ Будь ласка, прикріпіть відео/аудіо до команди або надішліть команду <code>/addmusic Назва</code> відповіддю на файл!",
            parse_mode=ParseMode.HTML
        )
        return

    song_id = await database.add_custom_song(
        title=title,
        author=author,
        file_id=file_id,
        file_type=file_type,
        added_by=message.from_user.id
    )

    await message.reply(
        f"✅ <b>Пісню успішно збережено в базу!</b>\n"
        f"• ID: <code>{song_id}</code>\n"
        f"• Назва: <b>{title}</b>\n"
        f"• Тип: <b>{file_type.upper()}</b>",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("delmusic"))
async def cmd_delmusic(message: types.Message, command: CommandObject):
    """Видалення пісні з бази за її ID."""
    is_admin = await check_admin_rights(message)
    if not is_admin:
        await message.reply("⚠️ Ця команда доступна лише для супер-адміна.")
        return

    if not command.args or not command.args.strip().isdigit():
        await message.reply("⚠️ Вкажіть ID пісні: <code>/delmusic [ID]</code>", parse_mode=ParseMode.HTML)
        return

    song_id = int(command.args.strip())
    success = await database.delete_custom_song(song_id)
    if success:
        await message.reply(f"✅ Пісню #{song_id} видалено з бази.")
    else:
        await message.reply(f"❌ Пісню з ID #{song_id} не знайдено.")


# ---------------- HTTP Health Check Server для Render ----------------
async def handle_health_check(request: web.Request) -> web.Response:
    """Відповідає 200 OK для запобігання засинанню бота на Render."""
    return web.Response(text="Ukrainian Patriotic MP4 Music Bot is running 24/7!", status=200)


async def start_web_server():
    """Запускає веб-сервер на потрібному порту Render.com."""
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.PORT)
    await site.start()
    logger.info(f"Health-check веб-сервер успішно запущено на порту {config.PORT}")


# ---------------- Головна функція запуску ----------------
async def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error("ПОМИЛКА: Не задано BOT_TOKEN у файлі .env або змінних середовища Render!")
        sys.exit(1)

    # 1. ЗАПУСК ВЕБ-СЕРВЕРА В ПЕРШУ ЧЕРГУ ДЛЯ RENDER (миттєве відкриття порту)
    try:
        await start_web_server()
    except Exception as e:
        logger.error(f"Помилка запуску веб-сервера: {e}")

    # 2. Ініціалізація бази даних
    await database.init_db()

    bot = Bot(token=config.BOT_TOKEN)

    # 3. Очищаємо вебхуки та старі запити для уникнення конфліктів
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning(f"Не вдалося скинути webhook: {e}")

    # 4. Запускаємо фоновий worker автоплею
    asyncio.create_task(auto_play_worker(bot))

    logger.info("Бот успішно підключився до Telegram та готовий до роботи!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), drop_pending_updates=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинений.")
