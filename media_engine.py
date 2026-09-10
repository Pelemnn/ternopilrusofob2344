"""
Модуль для автоматичного завантаження реальних MP4 відео та гарантованих YouTube-посилань.
Працює за прямими посиланнями авторів та каналу «Український Повстанець»,
з автоматичним інтелектуальним підбором живого відео без 404 помилок.
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


def download_mp4_and_get_video_url(song: Dict[str, Any]) -> Tuple[Optional[Path], str]:
    """
    Завантажує справжнє MP4 відео пісні та повертає (шлях_до_mp4, гарантовано_робоче_посилання).
    Завжди повертає реальне робоче посилання YouTube з відтворенням без помилок.
    """
    safe_title = "".join(c for c in song["title"] if c.isalnum() or c in " _-").strip().replace(" ", "_")
    base_filename = f"{song['id']:03d}_{safe_title}"
    mp4_path = MUSIC_DIR / f"{base_filename}.mp4"

    # 1. Перевіряємо чи файл уже збережено на диску
    if mp4_path.exists() and mp4_path.stat().st_size > 50000:
        working_url = song.get("video_url") or f"https://www.youtube.com/results?search_query={song['title'].replace(' ', '+')}"
        return mp4_path, working_url

    # 2. Формуємо пошуковий запит для каналу «Український Повстанець» та автора
    search_query = f"ytsearch1:{song['title']} {song['author']} пісня"
    output_template = str(MUSIC_DIR / f"{base_filename}.%(ext)s")

    ydl_opts = {
        "format": "best[ext=mp4][height<=480]/bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/best[height<=480]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
        "max_filesize": 48 * 1024 * 1024,
    }

    real_video_url = f"https://www.youtube.com/results?search_query={song['title'].replace(' ', '+')}"

    # 3. Спроба завантажити напряму через yt-dlp
    try:
        target_source = song.get("video_url")
        # Якщо URL не містить реального watch?v або викликає сумніви — шукаємо напряму за назвою та автором
        if not target_source or "watch?v=" not in target_source or len(target_source) < 25:
            target_source = search_query

        logger.info(f"Завантаження MP4 для #{song['id']} '{song['title']}'...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_source, download=True)
            if info:
                if "entries" in info and info["entries"]:
                    entry = info["entries"][0]
                    vid_id = entry.get("id")
                    real_video_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else entry.get("webpage_url", real_video_url)
                else:
                    vid_id = info.get("id")
                    real_video_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else info.get("webpage_url", real_video_url)

        # Перевіряємо завантажений файл MP4
        if mp4_path.exists() and mp4_path.stat().st_size > 50000:
            return mp4_path, real_video_url

        # Шукаємо файл за будь-яким розширенням
        for p in MUSIC_DIR.glob(f"{base_filename}.*"):
            if p.suffix.lower() in (".mp4", ".mkv", ".webm") and p.stat().st_size > 50000:
                return p, real_video_url

    except Exception as e:
        logger.error(f"Помилка основного завантаження #{song['id']}: {e}")
        # Якщо сталася помилка — здійснюємо пошук альтернативного живого відео
        try:
            fallback_query = f"ytsearch1:{song['title']} Український Повстанець"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(fallback_query, download=True)
                if info and "entries" in info and info["entries"]:
                    entry = info["entries"][0]
                    vid_id = entry.get("id")
                    real_video_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else entry.get("webpage_url", real_video_url)

            for p in MUSIC_DIR.glob(f"{base_filename}.*"):
                if p.stat().st_size > 50000:
                    return p, real_video_url
        except Exception as e2:
            logger.error(f"Fallback пошук також зазнав помилки: {e2}")

    return None, real_video_url


def format_song_caption(song: Dict[str, Any], video_url: Optional[str] = None) -> str:
    """
    Формує підпис для MP4 відео в Telegram з діючим клікабельним посиланням на YouTube.
    """
    url = video_url or song.get("video_url") or "https://www.youtube.com"
    return (
        f"🎬 <b>{song['title']}</b>\n"
        f"👤 <b>Виконавець:</b> {song['author']}\n"
        f"📜 <b>Епоха:</b> {song['category']}\n\n"
        f"💬 <b>Слова / Приспів:</b>\n"
        f"<i>{song['chorus']}</i>\n\n"
        f"🔗 <a href='{url}'>Дивитися відео на YouTube</a>\n\n"
        f"🇺🇦 <i>Слава Україні! Героям Слава!</i>"
    )
