"""
Modul helper untuk mengirim notifikasi via Telegram Bot.
Menggunakan python-telegram-bot 20.x (async API).
"""

import os
import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


async def _send_message_async(message):
    """
    Fungsi async internal untuk mengirim pesan ke grup Telegram.
    Args:
        message: Teks pesan yang akan dikirim.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum dikonfigurasi di .env")

    bot = Bot(token=bot_token)
    await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="HTML",
    )
    logger.info(f"Notifikasi Telegram berhasil dikirim ke chat {chat_id}")


def send_notification(message):
    """
    Mengirim notifikasi ke grup Telegram (sync wrapper).
    Menjalankan fungsi async di dalam event loop baru.
    Args:
        message: Teks pesan (mendukung format HTML).
    Returns:
        bool: True jika berhasil, False jika gagal.
    """
    try:
        # Cek apakah sudah ada event loop yang berjalan
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Jika sudah ada event loop (misalnya di dalam async context),
            # buat task baru
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _send_message_async(message))
                future.result(timeout=10)
        else:
            asyncio.run(_send_message_async(message))

        return True
    except TelegramError as e:
        logger.error(f"Gagal mengirim notifikasi Telegram: {e}")
        return False
    except Exception as e:
        logger.error(f"Error tidak terduga saat mengirim Telegram: {e}")
        return False
