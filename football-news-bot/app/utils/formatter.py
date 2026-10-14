"""Telegram HTML formatasi (aiogram parse_mode=HTML).

Talablar:
- Matn va URL'larni HTML escape qilish (xavfsizlik uchun).
- Xabar uzunligini Telegram limiti (4096) ichida ushlash — kerak bo'lsa
  qismlarga bo'lish.
"""

from __future__ import annotations

from datetime import datetime, timezone

from html import escape as _html_escape

from app.config import SAFE_MSG_LEN
from app.services.news_fetcher import NewsItem


def escape_html(text: str) -> str:
    """Matn/URL'ni Telegram HTML parse_mode uchun xavfsiz qiladi.

    Eslatma: Python'ning `html.escape(quote=True)` funksiyasi apostrofnı
    `&#x27;` ko'rinishida kodlaydi — bu Telegram'da yaroqsiz qoldiq entity
    sifatida ko'rinadi. Shu sababli `&#x27;` ni qayta `&apos;` ga
    almashtiramiz (Telegram HTML5 `<a>` ichida ham, tashqarisida ham
    `&apos;` ni to'g'ri qabul qiladi).
    """
    escaped = _html_escape(text or "", quote=True)
    return escaped.replace("&#x27;", "&apos;")

HEADER_TEMPLATE = (
    "⚽ <b>BUGUNGI FUTBOL YANGILIKLARI</b>\n"
    "📅 {date}\n\n"
)

ITEM_TEMPLATE = (
    "{idx}. 🔥 <b>{title}</b>\n"
    "{summary}\n"
    "🔗 <a href=\"{url}\">Manbani o'qish</a> ({source})\n"
)


def _today_str() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.day:02d}.{now.month:02d}.{now.year}"


def format_news_message(pairs: list[tuple[NewsItem, str]]) -> list[str]:
    """(item, uz_mazmun) juftliklaridan 1..N ta tayyor HTML xabar yasaydi.

    Har bir xabar SAFE_MSG_LEN (=3800) dan oshmaydi; oshsa yangiliklar
    ikkinchi xabarga ko'chiriladi.
    """
    if not pairs:
        return []

    chunks: list[str] = []
    current = HEADER_TEMPLATE.format(date=escape_html(_today_str()))

    for idx, (item, summary) in enumerate(pairs, start=1):
        piece = ITEM_TEMPLATE.format(
            idx=idx,
            title=escape_html(item.title),
            summary=escape_html(summary or ""),
            url=escape_html(item.url),   # URL ham escape qilinadi
            source=escape_html(item.source_name),
        )
        if len(current) + len(piece) > SAFE_MSG_LEN:
            chunks.append(current.rstrip())
            current = f"⚽ <b>Davomi...</b>\n\n{piece}"
        else:
            current += piece

    chunks.append(current.rstrip())
    return chunks


def format_no_news() -> str:
    return (
        "⚽ <b>Bugungi futbol yangiliklari topilmadi.</b>\n\n"
        "Afsuski, ayni paytda ishonchli manbalardan yangi xabar olib "
        "bo'lmadi. Birozdan keyin qayta urinib ko'ring."
    )


def format_error() -> str:
    return (
        "⚠️ Yangiliklarni yuklashda xatolik yuz berdi.\n"
        "Iltimos, birozdan so'ng qayta urinib ko'ring."
    )
