"""
Модуль для пошуку, завантаження аудіотреків з відео та формування повідомлень.
Використовує yt-dlp для отримання звукової доріжки пісні та посилання на відеокліп.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

import yt_dlp
from config import MUSIC_DIR

logger = logging.getLogger("media_engine")
MUSIC_DIR.mkdir(exist_ok=True)


def download_audio_and_get_video_url(song: Dict[str, Any]) -> Tuple[Optional[Path], str]:
    """
    Завантажує аудіодоріжку (M4A/MP3) для пісні та повертає (шлях_до_аудіо, посилання_на_відео).
    Якщо аудіо вже є на диску — повертає збережений файл.
    """
    safe_title = "".join(c for c in song["title"] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    base_filename = f"{song['id']:03d}_{safe_title}"

    # Перевіряємо чи файл вже завантажено раніше
    for ext in (".m4a", ".mp3", ".ogg", ".wav", ".opus", ".mp4"):
        existing = MUSIC_DIR / f"{base_filename}{ext}"
        if existing.exists() and existing.stat().st_size > 10000:
            video_url = f"https://www.youtube.com/results?search_query={song['title'].replace(' ', '+')}"
            return existing, video_url

    # Пошуковий запит для YouTube
    search_query = f"ytsearch1:{song['title']} {song['author']} пісня"
    output_template = str(MUSIC_DIR / f"{base_filename}.%(ext)s")

    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 12,
        "max_filesize": 20 * 1024 * 1024  # максимум 20 МБ
    }

    video_url = f"https://www.youtube.com/results?search_query={song['title'].replace(' ', '+')}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=True)
            if info and "entries" in info and info["entries"]:
                entry = info["entries"][0]
                video_url = entry.get("webpage_url") or entry.get("url") or video_url

            # Знаходимо щойно завантажений файл
            for ext in (".m4a", ".mp3", ".ogg", ".wav", ".opus", ".mp4"):
                downloaded = MUSIC_DIR / f"{base_filename}{ext}"
                if downloaded.exists() and downloaded.stat().st_size > 5000:
                    logger.info(f"Успішно завантажено аудіо для «{song['title']}»: {downloaded.name}")
                    return downloaded, video_url
    except Exception as e:
        logger.warning(f"Помилка завантаження аудіо через yt-dlp для «{song['title']}»: {e}")

    return None, video_url


def format_song_caption(song: Dict[str, Any], video_url: str) -> str:
    """Формує структурований патріотичний опис із посиланням на відео."""
    return (
        f"🎵 <b>{song['title']}</b>\n"
        f"🏷️ <i>Категорія: {song['category']}</i>\n"
        f"👤 <i>Автор / Походження: {song['author']}</i>\n\n"
        f"📜 <b>Приспів:</b>\n{song['chorus']}\n\n"
        f"🎬 <b>Дивитися відеокліп:</b> <a href=\"{video_url}\">▶️ Відкрити відео на YouTube</a>\n\n"
        f"🇺🇦 <i>Слава Україні! Героям Слава!</i>"
    )
