"""Loyiha konfiguratsiyasi.

Barcha maxfiy kalitlar .env fayli orqali o'qiladi — kod ichiga yozilmaydi.
RSS manbalari 2026-10-14 kuni haqiqiy so'rovlar bilan tekshirilgan:
faqat ishlayotgan (HTTP 200 + yangi pubDate) feedlar ro'yxatga kiritilgan.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class RssSource:
    name: str      # manba nomi (foydalanuvchiga ko'rsatiladi)
    url: str       # tekshirilgan RSS/Atom manzili
    category: str  # "main" | "transfer" | "cl" | "premier-league"


# --- Tekshirilgan, ishlaydigan RSS manbalari -------------------------------
# BBC Sport va Sky Sports o'zining rasmiy, barqaror RSS endpointlarini
# nashr etadi. Reuters/ESPN ochiq RSS bermaydi (tekshirildi: 403/404),
# shuning uchun ulardan foydalanilmaydi.
RSS_SOURCES: tuple[RssSource, ...] = (
    RssSource("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml", "main"),
    RssSource("Sky Sports", "https://www.skysports.com/rss/12040", "main"),
    RssSource("The Guardian", "https://www.theguardian.com/football/rss", "main"),
    RssSource("BBC Sport - Premier League", "https://feeds.bbci.co.uk/sport/football/premier-league/rss.xml", "premier-league"),
    RssSource("BBC Sport - Champions League", "https://feeds.bbci.co.uk/sport/football/champions-league/rss.xml", "cl"),
)

# Xabar uzunligi chegaralari
TELEGRAM_MAX_LEN = 4096          # Telegram xabar limiti
SAFE_MSG_LEN = 3800              # zaxira bilan
MAX_ITEMS = 10                   # eng ko'p chiqariladigan yangiliklar soni
MIN_ITEMS = 5                    # maqsadli minimal son (topilmasa kamroq chiqadi)

# Tarmoq sozlamalari
HTTP_TIMEOUT_SEC = 10.0
HTTP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 FootballNewsBot/1.0"
)


@dataclass
class Settings:
    bot_token: str = ""
    # Keyingi bosqichlar uchun (AI qisqartirish) — hozircha bo'sh qolsa ham ishlaydi:
    gemini_api_key: str = ""
    qwen_api_key: str = ""
    news_max_age_hours: int = 36   # "bugungi" deb hisoblash oynasi
    sources: tuple[RssSource, ...] = field(default_factory=lambda: RSS_SOURCES)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            bot_token=os.getenv("BOT_TOKEN", "").strip(),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            qwen_api_key=os.getenv("QWEN_API_KEY", "").strip(),
            news_max_age_hours=int(os.getenv("NEWS_MAX_AGE_HOURS", "36")),
        )


settings = Settings.from_env()
