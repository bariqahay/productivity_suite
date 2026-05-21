import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

async def test():
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID belum di-set di .env")
        return

    await bot.send_message(
        chat_id=chat_id,
        text="✅ Test notifikasi berhasil!"
    )
    print("Pesan terkirim.")

asyncio.run(test())