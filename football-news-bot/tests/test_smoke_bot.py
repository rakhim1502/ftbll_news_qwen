"""Bot oqimi (pipeline) bo'yicha smoke testlar.

Maqsad: tashqi tarmoqqa chiqmasdan, /start handler'ning to'liq zanjirini
(fetch -> rank -> summarize -> format -> Telegram answer) tekshirish.

Tarmoq so'rovlari monkeypatch bilan almashtiriladi, shuning uchun testlar
oflayn rejimda ham barqaror ishlaydi.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app.handlers import start as start_module
from app.services.news_fetcher import NewsItem


# --- Sahte ma'lumotlar ------------------------------------------------------

def _mk_item(i: int, title: str, url: str) -> NewsItem:
    now = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=i)
    return NewsItem(
        title=title,
        url=url,
        summary="Manchester City vs Liverpool match ended 2-1. Haaland scored twice.",
        published=now,
        source_name="BBC Sport",
    )


FAKE_ITEMS = [
    _mk_item(0, "Haaland signs new Manchester City deal & extends contract",
             "https://www.bbc.co.uk/sport/football/1"),
    _mk_item(1, "Real Madrid advance to Champions League quarter-finals",
             "https://www.bbc.co.uk/sport/football/2"),
    _mk_item(2, "Liverpool transfer chase for Bayern midfielder intensifies",
             "https://www.skysports.com/football/3"),
    _mk_item(3, "O'zbekiston national team announces squad for friendly match",
             "https://www.theguardian.com/football/4"),
    _mk_item(4, "Premier League clubs vote on new financial rules",
             "https://www.bbc.co.uk/sport/football/5"),
]


@pytest.fixture()
def patched_fetch(monkeypatch):
    """fetch_news'ni sahte RSS natijasi bilan almashtiradi (tarmoqqa chiqmaydi)."""

    async def fake_fetch(*args, **kwargs):
        return list(FAKE_ITEMS)

    monkeypatch.setattr(start_module, "fetch_news", fake_fetch)
    # AI kalitsiz muhitda translator tarmoqqa chiqmasligi kafolatlanadi,
    # lekin ehtiyot bo'lib summarize_items'ni ham stabil qilib qo'yamiz:
    async def fake_summarize(items):
        return [(it, "Qisqa o'zbekcha mazmun: " + it.title[:30]) for it in items]

    monkeypatch.setattr(start_module, "summarize_items", fake_summarize)
    return FAKE_ITEMS


class FakeMessage:
    """aiogram Message'ning minimal stub'i — faqat handler ishlatgan qismi."""

    def __init__(self, sent: list[str] | None = None, edited: list[str] | None = None):
        # Barcha javob xabarlari umumiy ro'yxatni bo'lishadi — shunda
        # progress xabarini edit qilganda ham matn bir joyda yig'iladi.
        self.sent = sent if sent is not None else []
        self.edited = edited if edited is not None else []
        self.from_user = type("U", (), {"full_name": "Test User"})()

    async def answer(self, text, **kwargs):
        self.sent.append(text)
        return FakeMessage(self.sent, self.edited)

    async def edit_text(self, text, **kwargs):
        self.edited.append(text)


async def test_start_pipeline_offline(patched_fetch):
    msg = FakeMessage()
    await start_module.cmd_start(msg)  # type: ignore[arg-type]

    all_texts = msg.sent + msg.edited
    joined = "\n".join(all_texts)

    # 1) Salomlashuv bor, foydalanuvchi ismi HTML-safe
    assert "Salom" in joined
    # 2) Xabar topilgan va bo'linma bilan yuborilgan
    news_msgs = [t for t in msg.sent if "BUGUNGI FUTBOL YANGILIKLARI" in t]
    assert news_msgs, "Yangiliklar xabari yuborilmadi"
    body = news_msgs[0]
    # 3) Har bir yangilik uchun alohida manba havolasi
    assert body.count("Manbani o'qish") >= 5 or body.count("Manbani o&#x27;qish") + body.count("Manbani o&apos;qish") >= 5
    # 4) XSS/escape tekshiruvi: & belgisi to'g'ri escape qilingan
    assert "&#x" not in body, "Yaroqsiz entity qoldig'i: &#x"
    assert "&amp;" in body  # 'deal & extends' sarlavhasidagi &
    # 5) URL'lar href ichida
    assert '<a href="https://www.bbc.co.uk/sport/football/1"' in body


async def test_start_no_news_message(monkeypatch):
    """Yangilik topilmasa — foydalanuvchiga ochiq xabar berilsin."""

    async def empty_fetch(*args, **kwargs):
        return []

    async def empty_summarize(items):
        return []

    monkeypatch.setattr(start_module, "fetch_news", empty_fetch)
    monkeypatch.setattr(start_module, "summarize_items", empty_summarize)

    msg = FakeMessage()
    await start_module.cmd_start(msg)  # type: ignore[arg-type]

    joined = "\n".join(msg.sent + msg.edited)
    assert "hozircha yangilik topilmadi" in joined.lower() or "topilmadi" in joined


async def test_start_error_resilience(monkeypatch):
    """Tarmoq xatosida bot ishlashdan to'xtamasligi kerak."""

    async def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(start_module, "fetch_news", boom)

    msg = FakeMessage()
    await start_module.cmd_start(msg)  # type: ignore[arg-type]

    joined = "\n".join(msg.sent + msg.edited)
    assert "Xatolik" in joined or "xato" in joined.lower()
    # Handler exception ko'tarmadi — bu testgacha yetib keldik
