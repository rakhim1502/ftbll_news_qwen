"""Buyruqlar: /start (yangiliklar) va /help (yoriqnoma).

/start oqimi:
1) Foydalanuvchini kutib olish.
2) "Yangiliklar izlanmoqda..." xabari.
3) RSS'dan yig'ish -> saralash -> qisqartirish -> HTML xabar(lar).
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.config import settings

from app.services.news_fetcher import fetch_news
from app.services.news_ranker import rank_news
from app.services.translator import summarize_items
from app.utils.formatter import format_error, format_news_message, format_no_news

logger = logging.getLogger(__name__)

router = Router()

HELP_TEXT = (
    "ℹ️ <b>Qanday ishlaydi?</b>\n\n"
    "📰 <b>/start</b> — bugungi eng muhim futbol yangiliklarini "
    "o\u2018zbek tilida yuboradi (BBC Sport, Sky Sports, The Guardian).\n"
    "ℹ️ <b>/help</b> — shu yoriqnomani ko\u2018rsatadi.\n\n"
    "Har bir yangilik bilan asl maqola havolasi beriladi. "
    "Yangiliklarni olish uchun <b>/start</b> yuboring!"
)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = message.from_user
    name = user.full_name if user else "do'st"

    await message.answer(
        f"Salom, <b>{name}</b>! 👋\n"
        "Men O'zbek tilidagi futbol yangiliklari botiman.⚽\n"
        "Sizga bugungi eng muhim futbol yangiliklarini "
        "ishonchli manbalardan yetkazaman.\n\n"
        "📰 <b>Yangiliklarni o'qiyapman...</b>",
        parse_mode="HTML",
    )

    progress = await message.answer(
        "⏳ Bir lahza — so'nggi yangiliklar tekshirilmoqda "
        "(BBC Sport, Sky Sports, The Guardian)…"
    )

    try:
        items = await fetch_news(max_age_hours=settings.news_max_age_hours)
        top = rank_news(items, max_items=10)
        pairs = await summarize_items(top)
        chunks = format_news_message(pairs)

        await progress.edit_text("✅ Tayyor! Natijalar yuborilmoqda…")

        if not chunks:
            await message.answer(format_no_news(), parse_mode="HTML")
        else:
            for chunk in chunks:
                await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)
    except Exception:  # noqa: BLE001 — bot ishlashdan to'xtamasligi kerak
        logger.exception("/start bajarilishida kutilmagan xato")
        await progress.edit_text(format_error(), parse_mode="HTML")
