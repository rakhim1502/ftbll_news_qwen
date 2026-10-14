"""Botni ishga tushiruvchi asosiy kirish nuqtasi.

Ishga tushirish:  python -m app.main
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.handlers.start import router as start_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError(
            "BOT_TOKEN topilmadi! .env fayliga BotFather'dan olingan "
            "tokenni kiriting: BOT_TOKEN=123456:ABC-DEF..."
        )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(start_router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot ishga tushdi. Long polling boshlandi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
