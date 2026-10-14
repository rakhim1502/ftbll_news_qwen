"""Xabarlarni saralash (ranking) va takrorlanishlarni olib tashlash.

Minimal MVP versiyasi:
- Bir xil URL yoki deyarli bir xil sarlavhali xabarlarni belgilaydi (dedupe).
- Muhimlik bo'yicha oddiy ball: so'nggi pubDate + kalit so'zlar
  (transfer, Champions League, terma jamoa, klub nomlari va h.k.).
- Eng yaxshi 5–10 tasini tanlaydi; yetarli bo'lmasa sun'iy to'ldirmaydi.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

from app.services.news_fetcher import NewsItem

# Muhimlik kalit so'zlar va ularning og'irliklari
KEYWORDS: dict[str, int] = {
    "transfer": 3, "signs": 2, "deal": 1, "loan": 1, "contract": 1,
    "champions league": 3, "europa league": 2, "world cup": 3,
    "premier league": 2, "la liga": 1, "serie a": 1, "bundesliga": 1,
    "final": 2, "semi-final": 2, "derby": 2, "injury": 2, "sack": 2,
    "manager": 1, "coach": 1, "national team": 2, "uzbekistan": 4,
    "real madrid": 1, "barcelona": 1, "manchester united": 1,
    "manchester city": 1, "liverpool": 1, "arsenal": 1, "chelsea": 1,
    "bayern": 1, "juventus": 1, "inter": 1, "psg": 1,
}

# Futbolga oid BO'LMAGAN sport turlari. Ba'zi manbalar (masalan, Sky Sports
# 12040 feed) umumiy sport yangiliklarini beradi — rugby, NFL, tennis, golf,
# F1, velosiped va ot poygasi xabarlari futbol botiga kirmasligi kerak.
NON_FOOTER_HINTS: tuple[str, ...] = (
    "/rugby", "/nfl", "/tennis", "/golf", "/f1/", "/motor-sport",
    "/cycling", "/racing", "/boxing", "/darts", "/snooker",
    "/cricket", "/athletics", "/swimming",
)


def is_football(item: NewsItem) -> bool:
    """Xabar futbolga tegishli ekanini URL/sarlavha bo'yicha tekshiradi.

    Qoida: avval ANIQ futbol belgisini izlaymiz (URL'dagi /football/ yo'li
    yoki sarlavhadagi futbol atamalari). "world cup", "final", "injury" kabi
    umumiy so'zlar rugby/NFL/tennis'da ham uchraydi — ularni asosiy belgi
    sifatida ISHLATMAYMIZ.
    """
    url = item.url.lower()
    title = item.title.lower()

    # 1) URL aniq boshqa sport turiga tegishli -> darhol rad etamiz
    if any(h in url for h in NON_FOOTER_HINTS):
        return False

    # 2) URL'dagi /football/ yoki /soccer/ yo'li — eng ishonchli belgi
    if re.search(r"/(football|soccer)/", url):
        return True

    # 3) Sarlavhadagi aniq futbol atamalari
    football_terms = (
        "football", "soccer", "futbol",
        "premier league", "champions league", "europa league", "conference league",
        "la liga", "bundesliga", "ligue 1", "eredivisie", "fa cup", "carabao",
        "nations league", "world cup qualifier", "wc qualifier",
        "fc ", "afc ", "cf ", "u21", "u-21", "women's super league",
        "goalkeeper", "striker", "midfielder", "winger", "clean sheet",
        "hat-trick", "red card", "match report", "team news", "line-up",
        "real madrid", "barcelona", "bayern", "juventus", "inter milan",
        "liverpool", "arsenal", "chelsea", "tottenham", "manchester united",
        "manchester city", "newcastle", "aston villa", "dortmund", "psg",
        "paris saint", "atletico", "napoli", "ac milan", "as roma",
        "celtic", "rangers", "ajax", "benfica", "porto",
    )
    return any(t in title for t in football_terms)


def _normalize_title(title: str) -> str:
    """Taqqoslash uchun sarlavhani soddalashtiradi (lower, punktuatsiyasiz)."""
    s = unicodedata.normalize("NFKD", title.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def deduplicate(items: list[NewsItem]) -> list[NewsItem]:
    """Bir xil URL yoki deyarli bir xil sarlavhali xabarlarni olib tashlaydi.

    Takrorlanganda eng yangi (katta pubDate) va manbasi 'birinchi' bo'lgan
    variant saqlanadi.
    """
    by_url: dict[str, NewsItem] = {}
    for it in sorted(items, key=lambda x: x.published, reverse=True):
        url_key = it.url.split("?")[0].rstrip("/")
        if url_key in by_url:
            continue
        # Sarlavha bo'yicha ham yaqin takrorlarni tekshiramiz
        norm = _normalize_title(it.title)
        if any(_normalize_title(existing.title) == norm for existing in by_url.values()):
            continue
        by_url[url_key] = it
    return list(by_url.values())


def score_item(item: NewsItem, now: datetime | None = None) -> float:
    """Xabarga muhimlik ballini beradi (yuqoriroq = muhimroq)."""
    now = now or datetime.now(timezone.utc)
    age_hours = max((now - item.published).total_seconds() / 3600.0, 0.0)

    # Yangilik balli: 0..10 (so'nggi 12 soatda 10, 36 soatda ~7)
    recency = max(0.0, 10.0 - age_hours * 0.08)

    text = f"{item.title} {item.summary}".lower()
    keyword = sum(w for k, w in KEYWORDS.items() if k in text)

    # Sarlavhadagi e'lon qilingan xabarlar ko'proq muhim hisoblanadi
    bonus = 0.0
    if re.search(r"\breports?\b|\bbbc\b|exclusive", text):
        bonus += 1.0
    if item.title.lower().startswith(("transfer news", "breaking")):
        bonus += 2.0

    return recency + keyword + bonus


def rank_news(items: list[NewsItem], min_items: int = 5, max_items: int = 10) -> list[NewsItem]:
    """Filtr (faqat futbol) + dedupe + saralash.

    Eng muhim `max_items` tagacha; kam bo'lsa shuncha qaytadi (sun'iy to'ldirmaydi).
    """
    football = [it for it in items if is_football(it)]
    unique = deduplicate(football)
    ranked = sorted(unique, key=score_item, reverse=True)
    result = ranked[:max_items]

    if len(result) < min_items:
        # Sun'iy ravishda to'ldirmaymiz — topilganini qaytamiz.
        pass
    return result
