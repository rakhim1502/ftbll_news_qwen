"""translator (MVP qisqartirish) testlari."""

from datetime import datetime, timezone

from app.services.news_fetcher import NewsItem
from app.services.translator import summarize_item


def make(title, summary=""):
    return NewsItem(
        title=title,
        url="https://example.com/a",
        summary=summary,
        published=datetime.now(timezone.utc),
        source_name="BBC Sport",
    )


async def test_summary_uses_title_when_no_description():
    s = await summarize_item(make("Arsenal win derby"))
    assert "Arsenal" in s
    assert s.endswith(".")


async def test_summary_adds_meaningful_sentence():
    item = make(
        "Luis Enrique extends PSG contract",
        "Live scoreboard. The coach agreed a new deal until 2028, the club says.",
    )
    s = await summarize_item(item)
    # Shablon/navigatsiya matni chiqmasligi kerak
    assert "scoreboard" not in s.lower()
    assert "contract" in s or "shartnoma" in s.lower()


async def test_summary_truncates_long_text():
    long = "Word " * 300
    s = await summarize_item(make("Big news", long))
    assert len(s) < 600  # Telegram xabari uzunligi nazorati uchun cheklangan


async def test_no_duplicate_title_in_summary():
    same = "Mbappe signs for Real Madrid"
    s = await summarize_item(make(same, same))
    assert s.lower().count("mbappe") == 1
