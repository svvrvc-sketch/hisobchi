import sys
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database.db import init_db
from handlers import start, finance, voice, smart_text, receipts

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("hisobchi_ai")

class ResilientAiohttpSession(AiohttpSession):
    """Tarmoqda uzilish bo'lganda so'rovni avtomatik 3 martagacha qayta urinuvchi sessiya"""
    async def make_request(self, bot, method, timeout=None):
        for attempt in range(3):
            try:
                return await super().make_request(bot, method, timeout)
            except TelegramNetworkError as e:
                if attempt == 2:
                    raise e
                logger.warning(f"Telegram tarmog'ida qisqa uzilish ({e}), qayta yuborilmoqda... [{attempt + 1}/3]")
                await asyncio.sleep(1)

async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN aniqlanmadi. .env faylini tekshiring!")
        return

    logger.info("Hisobchi AI bazasi initsializatsiya qilinmoqda...")
    await init_db()

    session = ResilientAiohttpSession()
    bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Routerni ro'yxatdan o'tkazish:
    # 1. Cheklar (Rasm Vision AI)
    # 2. Ovoz (STT)
    # 3. Start & Yordam
    # 4. Moliya (Xarajat, Daromad, Hisobotlar)
    # 5. Aqlli matn tahlili
    dp.include_router(receipts.router)
    dp.include_router(voice.router)
    dp.include_router(start.router)
    dp.include_router(finance.router)
    dp.include_router(smart_text.router)

    logger.info("💼 Hisobchi AI (Cho'ntak Buxgalteri) muvaffaqiyatli ishga tushdi va faol!")
    
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
            break
        except Exception as e:
            logger.warning(f"Telegram tarmog'iga ulanishda uzilish bo'ldi ({e}). 3 soniyadan keyin qayta ulanmoqda...")
            await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
