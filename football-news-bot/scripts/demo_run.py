"""Butun zanjirni Telegram'siz sinash uchun demo skripti.

Ishlatish (loyiha papkasidan):
    python scripts/demo_run.py

RSS'dan yangiliklarni oladi -> saralaydi -> qisqartiradi (AI bo'lsa AI,
bo'lmasa naqshli fallback) -> Telegram HTML formatida chop etadi.
Bot tokeni SHART EMAS.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Skriptni `python scripts/demo_run.py` deb ishga tushirganda app paketi topilsin:
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.news_fetcher import fetch_news          # noqa: E402
from app.services.news_ranker import rank_news            # noqa: E402
from app.services.translator import ai_enabled, summarize_items  # noqa: E402
from app.utils.formatter import format_news_message        # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


async def main() -> None:
    print("⏳ Yangiliklar yuklanmoqda...")
    items = await fetch_news()
    print(f"📥 {len(items)} ta xabar olingan (manbalar: "
          f"{', '.join(sorted({i.source_name for i in items})) or '—'})")

    top = rank_news(items)
    print(f"🎯 Saralangan: {len(top)} ta")

    if not top:
        print("❌ Bugungi yangilik topilmadi (manbalar javobsiz qolishi mumkin).")
        return

    pairs = await summarize_items(top)
    mode = "AI (Gemini/Qwen)" if ai_enabled() else "AI'siz fallback"
    print(f"✍️  Qisqartirish rejimi: {mode}\n")

    messages = format_news_message(pairs)
    for msg in messages:
        print("-" * 60)
        print(msg)
    print("-" * 60)
    print(f"✅ Tayyor: {len(messages)} ta xabar ({sum(len(m) for m in messages)} belgi)")


if __name__ == "__main__":
    asyncio.run(main())
