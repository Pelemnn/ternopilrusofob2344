"""
Головний файл запуску Telegram-бота «Анти-Русифікатор».
Підтримує адміністраторські команди (/mute, /unmute, /setfob, /settings),
відправку реальних MP4 пісень (/music), додавання треків адміном (/addmusic)
та безперервну роботу на Render.com.
"""

import sys
import os
import time
import random
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

from aiohttp import web, ClientSession, ClientTimeout
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatPermissions, FSInputFile, BufferedInputFile
from aiogram.exceptions import TelegramBadRequest

import config
import database
import detector
import phrases
import music_data

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("anti_rus_bot")

dp = Dispatcher()

# Директорія для локальних MP4/MP3 файлів
MUSIC_DIR = Path(__file__).resolve().parent / "music"
MUSIC_DIR.mkdir(exist_ok=True)

# Словник кулдауну команди /music (chat_id -> timestamp)
MUSIC_COOLDOWN: dict[int, float] = {}
MUSIC_COOLDOWN_SECONDS = 60


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


async def check_admin_rights(message: types.Message, chat_id: int, user_id: int) -> bool:
    """Перевіряє, чи має користувач права адміна (супер-адмін, адмін бота або чату)."""
    if user_id == config.SUPER_ADMIN_ID:
        return True

    if await database.is_bot_admin(chat_id, user_id):
        return True

    try:
        member = await message.chat.get_member(user_id)
        if member.status in ("creator", "administrator"):
            return True
    except Exception:
        pass

    return False


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обробник команди /start."""
    text = (
        "👋 <b>Привіт! Я бот «Анти-Русифікатор».</b>\n\n"
        "Моя місія — оберігати українські Telegram-чати від російської мови, окупаційних слів та матів.\n\n"
        "<b>Як мене використовувати:</b>\n"
        "1. Додайте мене у вашу групу або супергрупу.\n"
        "2. Надайте мені <b>права адміністратора</b> (блокування учасників та видалення повідомлень).\n"
        "3. Я автоматично слідкуватиму за чистотою чату!\n\n"
        "<b>Команди:</b>\n"
        "• /help — Список команд\n"
        "• /music — Патріотична пісня УПА у форматі MP4 (кд 1 хв)\n"
        "• /my_punishments — Моя статистика покарань\n"
        "• /top — Топ порушників чату\n\n"
        "<b>Команди для адмінів:</b>\n"
        "• /mute [причина] [термін] — Замутити порушника\n"
        "• /unmute — Зняти мут\n"
        "• /setfob — Призначити адміном бота\n"
        "• /settings — Налаштувати час мутів (1-7 кроки)\n"
        "• /addmusic [назва] — Додати нове MP4 відео в плейлист бота\n\n"
        "🇺🇦 <i>Слава Україні! Героям Слава!</i>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обробник команди /help."""
    text = (
        "📋 <b>Список команд бота:</b>\n\n"
        "🎵 <b>Музика та розваги:</b>\n"
        "• /music — Надіслати повстанську пісню УПА як MP4 відео (кулдаун 1 хв)\n"
        "• /my_punishments — Перевірити свій лічильник покарань\n"
        "• /top — Рейтинг порушників чату\n\n"
        "👮‍♂️ <b>Команди адміністратора:</b>\n"
        "• <code>/mute [причина] [термін]</code> (відповіддю) — Мут користувача (наприклад: <code>/mute спам 10m</code> або <code>/mute 36h</code>)\n"
        "• <code>/unmute</code> (відповіддю) — Зняти обмеження з користувача\n"
        "• <code>/setfob</code> (відповіддю) — Призначити адміном бота\n"
        "• <code>/settings</code> — Переглянути або налаштувати час мутів (наприклад: <code>/settings 1 36h</code>)\n"
        "• <code>/addmusic [назва]</code> (відповіддю на MP4 відео або в описі до відео) — Додати трек у базу бота\n"
        "• <code>/reset</code> (відповіддю) — Скинути лічильник покарань на 0\n"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("addmusic"))
async def cmd_addmusic(message: types.Message, command: CommandObject):
    """
    Додає нове MP4 відео / аудіо в базу даних бота через Telegram file_id.
    Адмін просто надсилає або відповідає на MP4 відео з командою /addmusic Назва пісні
    """
    is_admin = await check_admin_rights(message, message.chat.id, message.from_user.id)
    if not is_admin:
        await message.reply("❌ Ця команда доступна лише адміністраторам бота.")
        return

    # Перевіряємо відео в самому повідомленні або у повідомленні, на яке відповідають
    target_msg = message.reply_to_message if message.reply_to_message else message
    file_id = None
    file_type = "video"

    if target_msg.video:
        file_id = target_msg.video.file_id
        file_type = "video"
    elif target_msg.document and target_msg.document.mime_type and "video" in target_msg.document.mime_type:
        file_id = target_msg.document.file_id
        file_type = "video"
    elif target_msg.audio:
        file_id = target_msg.audio.file_id
        file_type = "audio"
    elif target_msg.voice:
        file_id = target_msg.voice.file_id
        file_type = "audio"

    if not file_id:
        await message.reply(
            "ℹ️ <b>Як додати MP4 пісню:</b>\n"
            "1. Надішліть у чат MP4 відео/музику з підписом: <code>/addmusic Назва пісні</code>\n"
            "2. Або відповідайте командою <code>/addmusic Назва пісні</code> на будь-яке відео в чаті.",
            parse_mode=ParseMode.HTML
        )
        return

    title = command.args.strip() if command.args else "Українська повстанська пісня"
    author = "ОУН-УПА / Народна"

    await database.add_custom_music(
        title=title,
        author=author,
        file_id=file_id,
        file_type=file_type,
        added_by=message.from_user.id
    )

    await message.reply(
        f"✅ <b>Пісню «{title}» успішно збережено у плейлист бота!</b>\n"
        f"Тепер бот буде надсилати її через команду <code>/music</code> як MP4 відео.",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("music"))
async def cmd_music(message: types.Message):
    """
    Відправляє випадкову повстанську пісню у форматі MP4 з кулдауном 1 хв:
    1. Перевіряє базу збережених MP4 треків (через file_id — миттєва відправка без затримок)
    2. Перевіряє локальну папку music/
    3. Використовує вбудовану колекцію з 30 пісень
    """
    chat_id = message.chat.id
    now = time.time()

    last_time = MUSIC_COOLDOWN.get(chat_id, 0)
    elapsed = now - last_time

    if elapsed < MUSIC_COOLDOWN_SECONDS:
        rem = int(MUSIC_COOLDOWN_SECONDS - elapsed)
        await message.reply(
            f"⏳ <b>Зачекайте ще {rem} сек</b> перед викликом наступної пісні!",
            parse_mode=ParseMode.HTML
        )
        return

    MUSIC_COOLDOWN[chat_id] = now

    # 1. Спроба відправити збережений адмінами MP4 трек через file_id
    custom_tracks = await database.get_all_custom_music()
    if custom_tracks:
        chosen = random.choice(custom_tracks)
        caption = (
            f"🎬 <b>{chosen['title']}</b>\n"
            f"👤 <i>{chosen['author']}</i>\n\n"
            f"🇺🇦 <i>Слава Україні! Героям Слава!</i>"
        )
        try:
            if chosen['file_type'] == "video":
                await message.answer_video(video=chosen['file_id'], caption=caption, parse_mode=ParseMode.HTML)
            else:
                await message.answer_audio(audio=chosen['file_id'], caption=caption, parse_mode=ParseMode.HTML)
            return
        except Exception as e:
            logger.warning(f"Помилка відправки custom file_id: {e}")

    # 2. Спроба відправити з локальної папки music/
    local_files = [f for f in MUSIC_DIR.glob("*") if f.suffix.lower() in ('.mp4', '.mp3', '.m4a', '.ogg')]
    if local_files:
        chosen_file = random.choice(local_files)
        caption = (
            f"🎬 <b>{chosen_file.stem}</b>\n"
            f"👤 <i>Українська повстанська пісня</i>\n\n"
            f"🇺🇦 <i>Слава Україні! Героям Слава!</i>"
        )
        try:
            if chosen_file.suffix.lower() == '.mp4':
                await message.answer_video(video=FSInputFile(chosen_file), caption=caption, parse_mode=ParseMode.HTML)
            else:
                await message.answer_audio(audio=FSInputFile(chosen_file), caption=caption, parse_mode=ParseMode.HTML)
            return
        except Exception as e:
            logger.warning(f"Помилка відправки локального файлу: {e}")

    # 3. Використання колекції з 30 пісень
    song = music_data.get_random_upa_song()
    caption_text = (
        f"🎬 <b>{song['title']}</b>\n"
        f"👤 <i>{song['author']}</i>\n\n"
        f"📜 {song['chorus']}\n\n"
        f"🎧 <a href=\"{song['link']}\">▶️ Слухати на YouTube</a>\n\n"
        f"🇺🇦 <i>Слава Україні! Героям Слава!</i>"
    )

    # Завантажуємо MP4 байти безпосередньо та відправляємо як відео
    mp4_url = song.get("mp4_url")
    if mp4_url:
        try:
            timeout = ClientTimeout(total=8)
            async with ClientSession(timeout=timeout) as session:
                async with session.get(mp4_url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        if len(content) > 1024:
                            video_input = BufferedInputFile(content, filename=f"{song['title']}.mp4")
                            await message.answer_video(
                                video=video_input,
                                caption=caption_text,
                                parse_mode=ParseMode.HTML
                            )
                            return
        except Exception as e:
            logger.warning(f"Не вдалося завантажити потокове MP4: {e}")

    # Резервний вивід з текстом та YouTube плеєром
    await message.answer(caption_text, parse_mode=ParseMode.HTML, disable_web_page_preview=False)


@dp.message(Command("mute"))
async def cmd_custom_mute(message: types.Message, command: CommandObject, bot: Bot):
    """
    Команда адміністратора /mute [причина] [термін]
    Приклади:
    - /mute спам 15m
    - /mute 2h образа
    - /mute 36h
    """
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Ця команда працює тільки в групах.")
        return

    is_admin = await check_admin_rights(message, message.chat.id, message.from_user.id)
    if not is_admin:
        await message.reply("❌ Ця команда доступна лише адміністраторам бота або чату.")
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply(
            "ℹ️ <b>Як використовувати:</b> Відповідайте цією командою на повідомлення порушника.\n"
            "Приклад: <code>/mute спам 10m</code> або <code>/mute 2h московитська мова</code> або <code>/mute 36h</code>",
            parse_mode=ParseMode.HTML
        )
        return

    target_user = message.reply_to_message.from_user
    if target_user.id == message.from_user.id:
        await message.reply("❌ Не можна замутити самого себе!")
        return

    # Парсинг аргументів
    args = command.args.strip() if command.args else ""
    tokens = args.split()

    duration_minutes = None
    reason_parts = []

    for token in tokens:
        parsed = config.parse_time_duration(token)
        if parsed and duration_minutes is None:
            duration_minutes = parsed
        else:
            reason_parts.append(token)

    if duration_minutes is None:
        duration_minutes = 15

    reason_text = " ".join(reason_parts) if reason_parts else "Порушення правил чату"
    until_date = datetime.now() + timedelta(minutes=duration_minutes)
    duration_str = config.format_duration_ukr(duration_minutes)

    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        target_mention = get_user_mention_html(target_user)
        admin_mention = get_user_mention_html(message.from_user)

        ans = (
            f"🔇 <b>Користувача {target_mention} замучено!</b>\n\n"
            f"⏳ <b>Тривалість:</b> {duration_str}\n"
            f"📝 <b>Причина:</b> {reason_text}\n"
            f"👮‍♂️ <b>Адміністратор:</b> {admin_mention}"
        )
        await message.answer(ans, parse_mode=ParseMode.HTML)
    except TelegramBadRequest as e:
        logger.error(f"Помилка при муті: {e}")
        await message.reply(f"❌ Не вдалося застосувати мут: {e}")


@dp.message(Command("unmute"))
async def cmd_unmute(message: types.Message, bot: Bot):
    """Зняття муту адміном."""
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    is_admin = await check_admin_rights(message, message.chat.id, message.from_user.id)
    if not is_admin:
        await message.reply("❌ Ця команда доступна тільки адміністраторам.")
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("ℹ️ Відповідайте цією командою на повідомлення користувача, якого хочете розмутити.")
        return

    target_user = message.reply_to_message.from_user
    try:
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


@dp.message(Command("setfob"))
async def cmd_setfob(message: types.Message, command: CommandObject):
    """Призначає користувача адміністратором бота."""
    is_admin = await check_admin_rights(message, message.chat.id, message.from_user.id)
    if not is_admin:
        await message.reply("❌ Тільки адміністратори бота можуть призначати нових адмінів.")
        return

    target_user_id = None
    target_user_name = ""

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id
        target_user_name = get_user_display_name(target_user)
    elif command.args and command.args.strip().isdigit():
        target_user_id = int(command.args.strip())
        target_user_name = f"ID:{target_user_id}"

    if not target_user_id:
        await message.reply(
            "ℹ️ <b>Як використовувати /setfob:</b>\n"
            "Відповідайте цією командою на повідомлення користувача, якого хочете зробити адміном бота, або вкажіть його ID:\n"
            "<code>/setfob 123456789</code>",
            parse_mode=ParseMode.HTML
        )
        return

    await database.add_bot_admin(
        chat_id=message.chat.id,
        user_id=target_user_id,
        user_name=target_user_name,
        added_by=message.from_user.id
    )

    await message.answer(
        f"🎖️ <b>Користувача {target_user_name} ({target_user_id}) призначено адміністратором бота!</b>\n"
        f"Тепер йому доступні команди модерації, налаштувань та муту.",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("settings"))
async def cmd_settings(message: types.Message, command: CommandObject):
    """Налаштування драбини покарань за 1-7 порушення."""
    is_admin = await check_admin_rights(message, message.chat.id, message.from_user.id)
    if not is_admin:
        await message.reply("❌ Ця команда доступна лише адміністраторам.")
        return

    ladder = await database.get_chat_mute_ladder(message.chat.id)

    if command.args:
        parts = command.args.strip().split()
        if len(parts) >= 2 and parts[0].isdigit():
            step_num = int(parts[0])
            time_val = config.parse_time_duration(parts[1])
            if 1 <= step_num <= 7 and time_val and time_val > 0:
                await database.set_chat_mute_step(message.chat.id, step_num, time_val)
                duration_str = config.format_duration_ukr(time_val)
                ladder = await database.get_chat_mute_ladder(message.chat.id)
                await message.answer(
                    f"✅ <b>Крок {step_num} оновлено!</b>\n"
                    f"Тепер за <b>{step_num}-те</b> порушення мут триватиме: <b>{duration_str}</b>.",
                    parse_mode=ParseMode.HTML
                )

    lines = ["⚙️ <b>Поточні налаштування мут-драбини для цього чату:</b>\n"]
    for i, minutes in enumerate(ladder, 1):
        d_str = config.format_duration_ukr(minutes)
        lines.append(f"• <b>{i}-й раз:</b> {d_str}")

    lines.append(
        "\n💡 <b>Щоб змінити будь-який крок:</b>\n"
        "Напишіть команду: <code>/settings [номер_кроку 1-7] [термін]</code>\n"
        "<i>Приклади:</i>\n"
        "• <code>/settings 1 36h</code> — встановити за 1-й раз мут на 36 годин\n"
        "• <code>/settings 2 1h</code> — встановити за 2-й раз мут на 1 годину\n"
        "• <code>/settings 7 3d</code> — встановити за 7-й раз мут на 3 доби"
    )
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)


@dp.message(Command("my_punishments"))
async def cmd_my_punishments(message: types.Message):
    """Показує кількість порушень того, хто викликав команду."""
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Ця команда доступна лише в групах.")
        return

    user_id = message.from_user.id
    count = await database.get_violation_count(message.chat.id, user_id)
    mention = get_user_mention_html(message.from_user)
    ladder = await database.get_chat_mute_ladder(message.chat.id)

    if count == 0:
        await message.answer(
            f"✨ {mention}, у вас <b>0 порушень</b>! Дякуємо, що спілкуєтеся солов'їною! 🇺🇦",
            parse_mode=ParseMode.HTML
        )
    else:
        next_duration = config.format_duration_ukr(config.get_next_mute_minutes(count, ladder))
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


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    """Скидання лічильника порушень адміном."""
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    is_admin = await check_admin_rights(message, message.chat.id, message.from_user.id)
    if not is_admin:
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
    """Основний обробник текстових повідомлень у групах."""
    if not message.from_user or message.from_user.is_bot:
        return

    text = message.text or message.caption
    if not text:
        return

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

    ladder = await database.get_chat_mute_ladder(message.chat.id)
    offense_count = await database.record_violation(message.chat.id, user.id, user_name)
    mute_minutes = config.get_mute_minutes(offense_count, ladder)
    until_date = datetime.now() + timedelta(minutes=mute_minutes)

    is_admin = await check_admin_rights(message, message.chat.id, user.id)

    if config.DELETE_OFFENDING_MESSAGE:
        try:
            await message.delete()
        except TelegramBadRequest as e:
            logger.warning(f"Не вдалося видалити повідомлення: {e}")

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
            logger.error(f"Помилка при спробі замутити: {e}")
    else:
        logger.info(f"Користувач {user.id} є адміністратором. Мут пропущено.")

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


# --- Render.com HTTP Health-Check Server ---
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
    logger.info(f"Запуск бота «Анти-Русифікатор» (Супер-адмін: {config.SUPER_ADMIN_ID})...")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
