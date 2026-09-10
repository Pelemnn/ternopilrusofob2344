"""
Головний файл запуску Telegram-бота «Патріотична Музика».
Завантажує та надсилає реальну аудіодоріжку пісні та посилання на повне відео:
1. Автоматично з налаштовуваним інтервалом (за замовчуванням кожні 10 хв).
2. За командою /music (або /song) у будь-який момент.
3. Налаштування інтервалу таймера через /settings [час].
4. Додавання власних аудіо/відео через /addmusic.
5. Працює 24/7 на Render.com.
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
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

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
    Завантажує звук із відео, надсилає аудіотрек у чат та додає посилання на відеокліп.
    """
    # 1. Перевіряємо кастомні завантажені треки через file_id
    custom_song = await database.get_random_song()
    if custom_song and random.random() < 0.25:
        caption = (
            f"🎵 <b>{custom_song['title']}</b>\n"
            f"👤 <i>{custom_song['author']}</i>\n\n"
            f"🇺🇦 <i>Слава Україні! Героям Слава!</i>"
        )
        try:
            if custom_song['file_type'] == "video":
                await bot.send_video(chat_id=chat_id, video=custom_song['file_id'], caption=caption, parse_mode=ParseMode.HTML)
            else:
                await bot.send_audio(chat_id=chat_id, audio=custom_song['file_id'], caption=caption, parse_mode=ParseMode.HTML)
            return True
        except Exception as e:
            logger.warning(f"Помилка відправки custom file_id: {e}")

    # 2. Вибираємо випадкову пісню зі 100 історичних пісень
    song = get_random_song_from_100()

    # Завантажуємо звук з відео у неблокуючому фоновому потоці
    audio_path, video_url = await asyncio.to_thread(media_engine.download_audio_and_get_video_url, song)
    caption = media_engine.format_song_caption(song, video_url)

    try:
        if audio_path and audio_path.exists():
            audio_file = FSInputFile(audio_path)
            await bot.send_audio(
                chat_id=chat_id,
                audio=audio_file,
                title=song["title"],
                performer=song["author"],
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        else:
            # Якщо завантаження заблоковано мережею — відправляємо структуроване повідомлення з відео
            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False
            )
        return True
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.warning(f"Не вдалося надіслати пісню у чат {chat_id}: {e}")
        return False


async def auto_play_worker(bot: Bot):
    """
    Фоновий процес: перевіряє чати кожні 20 секунд і надсилає пісню,
    якщо настав час згідно з індивідуальним інтервалом кожного чату.
    """
    logger.info("Фоновий таймер авто-відправки пісень запущено.")
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
        "У моїй базі зібрано <b>100 культових історичних пісень</b> (ОУН-УПА 1940-х, Січові Стрільці, Козацькі думи).\n\n"
        "Я <b>завантажую звук із відео</b>, надсилаю аудіотрек прямо в чат та додаю посилання на повний відеокліп:\n"
        "• ⏰ <b>Автоматично за таймером</b> (за замовчуванням кожні 10 хв)!\n"
        "• 🎵 За командою <code>/music</code> у будь-який момент!\n\n"
        "<b>Команди:</b>\n"
        "• /music або /song — Отримати випадкову пісню зараз\n"
        "• /settings [час] — Налаштувати таймер авто-відправки (наприклад: <code>/settings 5m</code>, <code>/settings 15m</code>, <code>/settings 1h</code>)\n"
        "• /list — Список 100 пісень у базі\n"
        "• /autoplay on|off — Увімкнути/вимкнути автоплей у чаті\n"
        "• /addmusic [назва] — Додати власне аудіо/відео (для адміна)\n\n"
        "🇺🇦 <i>Слава Україні! Героям Слава!</i>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обробник команди /help."""
    text = (
        "📋 <b>Список команд бота:</b>\n\n"
        "🎵 <b>Музика:</b>\n"
        "• /music або /song — Надіслати випадковий аудіотрек із посиланням на відео\n"
        "• /list — Переглянути каталог 100 історичних пісень\n\n"
        "⚙️ <b>Налаштування автоплею:</b>\n"
        "• <code>/settings</code> — Переглянути поточний інтервал відправки\n"
        "• <code>/settings [час]</code> — Встановити свій інтервал (наприклад: <code>/settings 5m</code>, <code>/settings 15m</code>, <code>/settings 30m</code>, <code>/settings 1h</code>)\n"
        "• <code>/autoplay on</code> або <code>/autoplay off</code> — Увімкнути/вимкнути автоплей\n\n"
        "👮‍♂️ <b>Для адміністраторів:</b>\n"
        "• <code>/addmusic [назва]</code> (відповіддю на аудіо/відео або з файлом) — Додати трек у базу\n"
        "• <code>/delmusic [ID]</code> — Видалити пісню за номером\n"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("music", "song", "play"))
async def cmd_music(message: types.Message, bot: Bot):
    """Миттєва відправка випадкової пісні зі 100 шедеврів."""
    chat_title = message.chat.title or message.from_user.full_name or "Chat"
    await database.register_chat(message.chat.id, chat_title)

    await send_random_song(bot, message.chat.id)


@dp.message(Command("settings"))
async def cmd_settings(message: types.Message, command: CommandObject):
    """Налаштування інтервалу авто-відправки пісень у чаті."""
    is_admin = await check_admin_rights(message)
    if not is_admin and message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.reply("❌ Змінювати налаштування чату можуть лише адміністратори.")
        return

    if command.args:
        parsed_min = config.parse_time_duration(command.args.strip())
        if parsed_min and parsed_min > 0:
            await database.set_chat_interval(message.chat.id, parsed_min)
            duration_str = config.format_duration_ukr(parsed_min)
            await message.answer(
                f"✅ <b>Інтервал оновлено!</b>\n"
                f"Тепер бот автоматично надсилатиме нову пісню кожні <b>{duration_str}</b>.",
                parse_mode=ParseMode.HTML
            )
            return
        else:
            await message.reply(
                "❌ Неправильний формат часу.\n"
                "Приклади: <code>/settings 5m</code>, <code>/settings 15m</code>, <code>/settings 30m</code>, <code>/settings 1h</code>, <code>/settings 2h</code>",
                parse_mode=ParseMode.HTML
            )
            return

    settings = await database.get_chat_settings(message.chat.id)
    status_str = "Увімкнено ▶️" if settings["autoplay_enabled"] else "Вимкнено ⏹️"
    duration_str = config.format_duration_ukr(settings["interval_minutes"])

    text = (
        f"⚙️ <b>Налаштування автоплею для цього чату:</b>\n\n"
        f"• <b>Статус:</b> {status_str}\n"
        f"• <b>Поточний інтервал:</b> кожні <b>{duration_str}</b>\n\n"
        f"💡 <b>Як змінити інтервал:</b>\n"
        f"Напишіть: <code>/settings [час]</code>\n\n"
        f"<i>Приклади:</i>\n"
        f"• <code>/settings 5m</code> — кожні 5 хвилин\n"
        f"• <code>/settings 10m</code> — кожні 10 хвилин (стандарт)\n"
        f"• <code>/settings 15m</code> — кожні 15 хвилин\n"
        f"• <code>/settings 30m</code> — кожні 30 хвилин\n"
        f"• <code>/settings 1h</code> — щогодини\n"
        f"• <code>/settings 2h</code> — кожні 2 години"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("autoplay"))
async def cmd_autoplay(message: types.Message, command: CommandObject):
    """Управління авто-відправкою."""
    arg = command.args.strip().lower() if command.args else ""
    if arg in ("off", "0", "вимк", "вимкнути"):
        await database.set_autoplay(message.chat.id, False)
        await message.answer("⏹️ Автоматичну відправку пісень <b>вимкнено</b> для цього чату.", parse_mode=ParseMode.HTML)
    elif arg in ("on", "1", "увімк", "увімкнути"):
        await database.set_autoplay(message.chat.id, True)
        settings = await database.get_chat_settings(message.chat.id)
        duration_str = config.format_duration_ukr(settings["interval_minutes"])
        await message.answer(f"▶️ Автоматичну відправку пісень <b>увімкнено</b> (інтервал: кожні {duration_str})!", parse_mode=ParseMode.HTML)
    else:
        await message.reply(
            "ℹ️ <b>Як використовувати:</b>\n"
            "• <code>/autoplay on</code> — увімкнути авто-відправку\n"
            "• <code>/autoplay off</code> — вимкнути авто-відправку",
            parse_mode=ParseMode.HTML
        )


@dp.message(Command("addmusic"))
async def cmd_addmusic(message: types.Message, command: CommandObject):
    """Додавання власного треку у базу бота (для адміна)."""
    is_admin = await check_admin_rights(message)
    if not is_admin:
        await message.reply("❌ Додавати пісні можуть лише адміністратори.")
        return

    target_msg = message.reply_to_message if message.reply_to_message else message
    file_id = None
    file_type = "audio"

    if target_msg.audio:
        file_id = target_msg.audio.file_id
        file_type = "audio"
    elif target_msg.video:
        file_id = target_msg.video.file_id
        file_type = "video"
    elif target_msg.document:
        file_id = target_msg.document.file_id
        file_type = "audio"

    if not file_id:
        await message.reply(
            "ℹ️ <b>Як додати свій трек:</b>\n"
            "1. Надішліть аудіо або відео файл із підписом: <code>/addmusic Назва пісні</code>\n"
            "2. Або відповідайте командою <code>/addmusic Назва</code> на будь-який аудіо/відео файл.",
            parse_mode=ParseMode.HTML
        )
        return

    title = command.args.strip() if command.args else "Українська патріотична пісня"
    author = "ОУН-УПА / Народна"

    await database.add_song(
        title=title,
        author=author,
        file_id=file_id,
        file_type=file_type,
        added_by=message.from_user.id
    )

    await message.reply(
        f"✅ <b>Пісню «{title}» успішно додано!</b>\n"
        f"Тепер вона буде в ротації автоплею та за командою /music.",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    """Відображає каталог 100 пісень та додані користувацькі треки."""
    custom_songs = await database.get_all_songs()

    upa_count = sum(1 for s in SONGS_100 if "УПА" in s["category"])
    uss_count = sum(1 for s in SONGS_100 if "УСС" in s["category"])
    cossack_count = sum(1 for s in SONGS_100 if "Козацька" in s["category"] or "Стародавня" in s["category"])

    text = (
        "📚 <b>Каталог зі 100 історичних українських пісень:</b>\n\n"
        f"• 🗡️ <b>Пісні ОУН-УПА (1940-ві роки):</b> {upa_count} пісень\n"
        f"• 🦅 <b>Пісні Січових Стрільців (УСС 1914–1920):</b> {uss_count} пісень\n"
        f"• 🐎 <b>Старовинні Козацькі та Повстанські думи:</b> {cossack_count} пісень\n"
        f"• 🎵 <b>Всього у колекції:</b> 100 культових творів!\n"
    )

    if custom_songs:
        text += f"\n⭐ <b>Додатково завантажено адмінами:</b> {len(custom_songs)} треків."

    text += "\n\n💡 <i>Надішліть /music, щоб отримати аудіотрек із посиланням на відео просто зараз!</i>"
    await message.answer(text, parse_mode=ParseMode.HTML)


# --- Render.com HTTP Health-Check Server ---
async def handle_health_check(request):
    return web.Response(text="Ukrainian Music Bot (100 Historic Songs) is running! 🇺🇦", content_type="text/plain")


async def start_web_server(port: int):
    """Запускає HTTP сервер для проходження health check на Render.com"""
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"HTTP health-check сервер запущено на порту {port} (для Render.com)")


async def main():
    """Точка входу в програму."""
    if not config.BOT_TOKEN:
        logger.critical(
            "ПОМИЛКА: Не вказано BOT_TOKEN!\n"
            "Створіть файл .env або додайте змінну оточення BOT_TOKEN у налаштуваннях Render."
        )
        sys.exit(1)

    await database.init_db()
    logger.info("База даних SQLite успішно ініціалізована.")

    port_env = os.getenv("PORT")
    if port_env:
        try:
            port = int(port_env)
            await start_web_server(port)
        except Exception as e:
            logger.warning(f"Не вдалося запустити health-check сервер на порту {port_env}: {e}")

    bot = Bot(token=config.BOT_TOKEN)
    logger.info(f"Запуск бота Музики УПА на 100 пісень (Супер-адмін: {config.SUPER_ADMIN_ID})...")

    # Запуск фонового процесу авто-відправки
    asyncio.create_task(auto_play_worker(bot))

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
