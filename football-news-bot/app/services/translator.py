"""Yangiliklarni o'zbek tiliga tarjima qilish / qisqartirish.

MVP (1-bosqich): AI kaliti bo'lmasa ham bot ishlashi uchun oddiy
lug'at asosidagi "pseudotarjima" + sarlavha/tavsifni birlashtirish.
Bu faktlarni o'zgartirmaydi — faqat tushunarli ko'rinishga keltiradi.

2-bosqichda shu interfeys orqali Gemini yoki Qwen API ulanadi
(sistem prompt: "faqat berilgan matnga tayangan holda 2-3 jumlada
o'zbekcha qisqartir, hech narsani to'qiyma").
"""

from __future__ import annotations

import re

from app.services.news_fetcher import NewsItem

# Kichik ko'p uchraydigan sport so'zlari lug'ati (faktlarni o'zgartirmaydi)
_UZ_TERMS: dict[str, str] = {
    "transfer news": "Transfer yangiliklari",
    "champions league": "Chempionlar ligasi",
    "premier league": "Premyer-liga",
    "world cup": "Jahon kubogi",
    "breaking": "Tezkor",
    "reports": "xabar qilmoqda",
    "says": "deb ma'lum qildi",
    "injury": "jarohat",
    "manager": "murabbiy",
    "coach": "murabbiy",
    "deal": "kelishuv",
    "signs": "shartnoma imzoladi",
    "draw": "durrang",
    "win": "g'alaba",
    "loss": "mag'lubiyat",
}


def _light_uz(text: str) -> str:
    """Matndagi aytilgan iboralarni o'zbekchalashtiradi (so'zma-so'z, fakt saqlanadi)."""
    out = text
    for en, uz in _UZ_TERMS.items():
        out = re.sub(rf"\b{re.escape(en)}\b", uz, out, flags=re.IGNORECASE)
    return out


def _truncate(text: str, limit: int = 260) -> str:
    """Tavsifni cheklangan uzunlikda ushlab qoladi (jumla chegarasida)."""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # oxirgi to'liq jumlagacha kesamiz
    for sep in (". ", "! ", "? "):
        idx = cut.rfind(sep)
        if idx > limit // 2:
            return cut[: idx + 1]
    idx = cut.rfind(" ")
    return (cut[:idx] + "…") if idx > 0 else cut[:limit] + "…"


def _first_sentences(text: str, max_sentences: int = 2, min_len: int = 40) -> str:
    """Matndan mazmunli birinchi jumlalarni saralaydi.

    RSS tavsiflarida ko'pincha navigatsiya/shablon matn ('Live scoreboard',
    'Email us', 'Today's Football' kabi) bo'ladi — ularni tashlab,
    eng uzun va ma'noli jumlani olamiz. Faktlar o'zgarmaydi, faqat tanlanadi.
    """
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    noise = re.compile(
        r"\b(live scoreboard|email (us|michael|a-z)|sign up|today.s football|"
        r"news from the|kick-?off|click to|subscribe|podcast|newsletter)\b",
        re.IGNORECASE,
    )
    good = [
        p.strip() for p in parts
        if len(p.strip()) >= min_len and not noise.search(p)
    ]
    if not good:
        # Butun matn shablon bo'lsa — hech bo'lmasa eng uzun qismni olamiz
        good = sorted((p.strip() for p in parts if len(p.strip()) >= 25), key=len, reverse=True)[:1]
    return ". ".join(good[:max_sentences])


async def summarize_item(item: NewsItem) -> str:
    """Bitta xabar uchun o'zbekcha qisqa mazmun qaytaradi.

    MVP: sarlavha + RSS tavsifi asosida (AI'siz).
    Keyingi bosqich: agar GEMINI_API_KEY/QWEN_API_KEY bo'lsa, shu funksiya
    ichida API'ga murojaat qilinadi (fallback shu yerda qoladi).
    """
    parts: list[str] = []
    title = _light_uz(item.title)
    if item.summary and _normalize(item.summary) != _normalize(item.title):
        meaningful = _first_sentences(item.summary)
        if meaningful and _normalize(meaningful) != _normalize(item.title):
            parts.append(_light_uz(_truncate(meaningful)))
    # Sarlavha tavsifda qoplangan bo'lsa uni takrorlamaymiz, aks holda boshiga qo'yamiz
    if title and not any(_normalize(title) in _normalize(p) for p in parts):
        parts.insert(0, title)
    text = ". ".join(p.rstrip(".") for p in parts if p)
    return (text + ".") if text and not text.endswith(".") else text


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", s.lower()).strip()


async def summarize_items(items: list[NewsItem]) -> list[tuple[NewsItem, str]]:
    """Xabarlar ro'yxatini (item, uz_mazmun) juftliklariga aylantiradi."""
    return [(it, await summarize_item(it)) for it in items]
