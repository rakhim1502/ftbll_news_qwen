"""Yangiliklarni o'zbek tiliga tarjima qilish / qisqartirish.

AI rejimi (GEMINI_API_KEY yoki QWEN_API_KEY .env'da to'ldirilgan bo'lsa):
- Modelga FAQAT olingan maqola ma'lumotlari (sarlavha + RSS tavsifi) beriladi.
- Sistem prompt faktlarni to'qiymaslikni qat'iy taqiqlaydi.
- Javob tekshiriladi; xato/bo'sh bo'lsa avtomatik fallback ishlaydi.

Fallback rejimi (AI kalitlari bo'lmasa — standart holat):
- Sarlavha + RSS tavsifidagi eng mazmunli jumlalarni tanlab, kichik
  lug'at bilan o'zbekchalashtiradi. Faktlarni o'zgartirmaydi.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

import httpx

from app.config import settings
from app.services.news_fetcher import NewsItem

logger = logging.getLogger(__name__)

AI_TIMEOUT_SEC = 20.0

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
    """Matndagi aytilgan iboralarni o'zbekchalashtiradi (so'zma-so'z, fakt saqlanadi).

    Eslatma: avval `&` belgisini himoya qilamiz (&amp;, &quot; kabi entity
    qoldiqlari ichidagi so'zlarni tarjima qilib buzmang).
    """
    protected = text.replace("&", "\x00")
    out = protected
    for en, uz in _UZ_TERMS.items():
        out = re.sub(rf"\b{re.escape(en)}\b", uz, out, flags=re.IGNORECASE)
    return out.replace("\x00", "&")


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


# ---------------------------------------------------------------------------
# AI qisqartirish (Gemini / Qwen) — kalitlar .env orqali, kod ichida yo'q
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "Sen futbol yangiliklarini o'zbek tiliga tarjima qiluvchi yordamchisan. "
    "Quyidagi MAQOLA SARLVHASI va TAQRIZIGA tayangan holda 2-3 ta qisqa, "
    "tabiiy o'zbek jumlasida xulosa yoz. QAT'IY QOIDALAR: "
    "1) Faqat berilgan matndagi faktlardan foydalan — hech qanday yangi "
    "ma'lumot, sana, nom yoki tafsilot QO'SHMA (to'qiyma). "
    "2) Futbolchi va klub nomlarini asl ko'rinishida saqlab qol. "
    "3) Berilgan matnda yetarli ma'lumot bo'lmasa, faqat sarlavhani tabiiy "
    "o'zbekcha qilib yoz. "
    "4) Javobda FAQAT o'zbekcha matn bo'lsin — izoh, prefiks yoki markdown YO'Q."
)


def _build_user_prompt(item: NewsItem) -> str:
    return (
        f"MANBA: {item.source_name}\n"
        f"MAQOLA SARLVHASI: {item.title}\n"
        f"TAQRIZ: {(item.summary or '(yo\'q)')[:900]}"
    )


def ai_enabled() -> bool:
    return bool(settings.gemini_api_key or settings.qwen_api_key)


async def _call_gemini(client: httpx.AsyncClient, item: NewsItem) -> str:
    """Google Gemini REST API (generativelanguage v1beta).

    Model nomi GEMINI_MODEL env o'zgaruvchisi bilan sozlanadi — Google
    eski modellarni deprecate qilganda kodni o'zgartirish talab qilinmaydi.
    """
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": _build_user_prompt(item)}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 200},
    }
    resp = await client.post(
        url,
        params={"key": settings.gemini_api_key},
        json=payload,
        timeout=AI_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _call_qwen(client: httpx.AsyncClient, item: NewsItem) -> str:
    """Qwen — DashScope OpenAI-compatible chat/completions endpoint.

    Model nomi QWEN_MODEL env o'zgaruvchisi bilan sozlanadi.
    """
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    payload = {
        "model": settings.qwen_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(item)},
        ],
        "temperature": 0.2,
        "max_tokens": 200,
    }
    resp = await client.post(
        url,
        headers={"Authorization": f"Bearer {settings.qwen_api_key}"},
        json=payload,
        timeout=AI_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


async def _ai_summarize(item: NewsItem) -> str | None:
    """Mavjud kalit bilan qisqartirish; har qanday xatoda None (fallback)."""
    try:
        async with httpx.AsyncClient() as client:
            if settings.gemini_api_key:
                text = await _call_gemini(client, item)
            else:
                text = await _call_qwen(client, item)
        # Javobni tekshirish: bo'sh emas, juda uzun emas, HTML bo'laklari yo'q
        text = re.sub(r"\s+", " ", text or "").strip()
        if not text or len(text) > 600 or "<" in text:
            logger.warning("AI javobi yaroqsiz (%s): %r", item.title[:40], text[:80])
            return None
        return text
    except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError, asyncio.TimeoutError) as exc:
        logger.warning("AI xatosi (%s): %s", item.title[:40], exc)
        return None


async def _strip_leaked_entities(text: str) -> str:
    """Matnda qolgan HTML entity kodlarini (&quot;, &apos; va h.k.) sof belgilarga ochadi.

    Ba'zi manbalar (masalan, Sky Sports tavsifi) CDATA ichida ikki qatlamli
    escape ishlatadi — parse'dan keyin ham `&quot;` ko'rinishidagi qoldiqlar
    qolishi mumkin. Bu funksiya yakuniy chiqishdan oldin ularni ochadi.
    """
    if "&" not in text:
        return text
    import html as _html

    prev = None
    out = text
    # Bir necha qatlam bo'lsa ham — to qoldiq qolmaguncha ochamiz
    while prev != out and "&" in out:
        prev = out
        out = _html.unescape(out)
    # Ochib bo'lmaydigan yaroqsiz kodlarni (&#x zarranglari) olib tashlaymiz
    out = re.sub(r"&(?:#x[0-9A-Fa-f]*|#\d*|[A-Za-z0-9]*);?", "", out)
    return out


async def summarize_item(item: NewsItem) -> str:
    """Bitta xabar uchun o'zbekcha qisqa mazmun qaytaradi.

    AI kaliti bo'lsa -> Gemini/Qwen; aks holda yoki xatoda -> fallback (AI'siz).
    """
    if ai_enabled():
        ai_text = await _ai_summarize(item)
        if ai_text:
            ai_text = await _strip_leaked_entities(ai_text)
            return ai_text if ai_text.endswith((".", "!", "?")) else ai_text + "."
    # --- Fallback (AI'siz) ---
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
    text = (text + ".") if text and not text.endswith(".") else text
    return await _strip_leaked_entities(text)


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", s.lower()).strip()


async def summarize_items(items: list[NewsItem]) -> list[tuple[NewsItem, str]]:
    """Xabarlar ro'yxatini (item, uz_mazmun) juftliklariga aylantiradi.

    AI yoqilgan bo'lsa, so'rovlar parallel bajariladi (har biriga limit),
    tartib saqlanadi.
    """
    if ai_enabled() and items:
        sem = asyncio.Semaphore(4)  # API rate-limit'dan himoya

        async def _one(it: NewsItem) -> tuple[NewsItem, str]:
            async with sem:
                return it, await summarize_item(it)

        return list(await asyncio.gather(*(_one(it) for it in items)))

    return [(it, await summarize_item(it)) for it in items]
