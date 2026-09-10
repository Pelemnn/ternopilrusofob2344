"""
Модуль для завантаження MP4 відео пісень за прямими посиланнями авторів.
Використовує yt-dlp для отримання справжнього MP4 відеофайлу та збереження на диск.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import yt_dlp
from config import MUSIC_DIR

logger = logging.getLogger("media_engine")
MUSIC_DIR.mkdir(exist_ok=True)


def download_mp4_video(song: Dict[str, Any]) -> Optional[Path]:
    """
    Завантажує справжній MP4 відеофайл пісні напряму за її конкретним посиланням (video_url).
    Кешує файл у папці music/, щоб не качати повторно.
    """
    safe_title = "".join(c for c in song["title"] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    base_filename = f"{song['id']:03d}_{safe_title}"
    mp4_path = MUSIC_DIR / f"{base_filename}.mp4"

    # 1. Якщо MP4 вже завантажено на диск і файл не порожній — повертаємо його
    if mp4_path.exists() and mp4_path.stat().st_size > 50000:
        return mp4_path

    # Також перевіряємо інші відео розширення, якщо yt-dlp зберіг як mkv/webm
    for ext in (".mp4", ".mkv", ".webm"):
        cached = MUSIC_DIR / f"{base_filename}{ext}"
        if cached.exists() and cached.stat().st_size > 50000:
            return cached

    video_url = song.get("video_url")
    if not video_url:
        return None

    output_template = str(MUSIC_DIR / f"{base_filename}.%(ext)s")

    ydl_opts = {
        # Пріоритет на MP4 відео в якості до 720p і розміром до 48 МБ (ліміт Telegram Bot API 50 МБ)
        "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 25,
        "max_filesize": 48 * 1024 * 1024,
    }

    try:
        logger.info(f"Завантаження MP4 для пісні #{song['id']} '{song['title']}' з {video_url}...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        if mp4_path.exists() and mp4_path.stat().st_size > 50000:
            logger.info(f"MP4 успішно завантажено: {mp4_path} ({mp4_path.stat().st_size / 1024 / 1024:.2f} MB)")
            return mp4_path

        # Перевірка інших відео файлів
        for p in MUSIC_DIR.glob(f"{base_filename}.*"):
            if p.suffix.lower() in (".mp4", ".mkv", ".webm") and p.stat().st_size > 50000:
                return p

    except Exception as e:
        logger.error(f"Помилка основного завантаження MP4 з {video_url}: {e}")
        # Fallback спроба завантажити легше відео
        try:
            fallback_opts = {
                "format": "best[height<=480][filesize<45M]/worst[ext=mp4]/worst",
                "outtmpl": output_template,
                "merge_output_format": "mp4",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 25,
            }
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                ydl.download([video_url])

            for p in MUSIC_DIR.glob(f"{base_filename}.*"):
                if p.stat().st_size > 50000:
                    return p
        except Exception as e2:
            logger.error(f"Fallback завантаження також зазнало помилки: {e2}")

    return None


def format_song_caption(song: Dict[str, Any], video_url: Optional[str] = None) -> str:
    """
    Формує естетичний підпис для MP4 відео в Telegram.
    """
    url = video_url or song.get("video_url") or "https://www.youtube.com"
    return (
        f"🎬 <b>{song['title']}</b>\n"
        f"👤 <b>Виконавець:</b> {song['author']}\n"
        f"📜 <b>Епоха:</b> {song['category']}\n\n"
        f"💬 <b>Слова / Приспів:</b>\n"
        f"<i>{song['chorus']}</i>\n\n"
        f"🔗 <a href='{url}'>Оригінал відео на YouTube</a>\n\n"
        f"🇺🇦 <i>Слава Україні! Героям Слава!</i>"
    )
