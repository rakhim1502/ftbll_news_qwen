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


async def test_leaked_entities_are_resolved(monkeypatch):
    """Sky Sports kabi manbalardan qolgan &quot;/&apos; qoldiqlari ochiladi."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    item = make(
        "What is wrong with Bruno Fernandes?",
        'A day before Manchester United&apos;s trip the club issued a statement '
        'on an &quot;jarohat niggle&quot; but stressed there was nothing to worry about.',
    )
    s = await summarize_item(item)
    assert "&quot;" not in s and "&apos;" not in s and "&#x" not in s
    # Faktlar saqlanadi, matnda oddiy tiriq belgilari bo'ladi
    assert "'" in s or '"' in s


def test_light_uz_does_not_break_entities():
    """&amp; ichidagi 'amp' so'zini tarjima qilib 'g'alaba'ga aylantirmasin."""
    from app.services.translator import _light_uz

    assert _light_uz("News &amp; views: team wins") == "News &amp; views: team g'alaba"
    # oddiy holatda ham entity buzilmaydi
    assert _light_uz("A &amp; B") == "A &amp; B"
