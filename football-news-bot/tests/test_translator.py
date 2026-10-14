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
    """&amp; ichidagi 'amp' so'zini tarjima qilib buzmasin."""
    from app.services.translator import _light_uz

    # "wins" so'zi lug'atda yo'q (faqat "win" bor) — shu sabab o'zgarmaydi;
    # eng muhimi: &amp; ichidagi "amp" -> "g'alaba" bo'lib ketmaydi
    assert _light_uz("News &amp; views: team wins") == "News &amp; views: team wins"
    # oddiy holatda ham entity buzilmaydi
    assert _light_uz("A &amp; B") == "A &amp; B"
    # to'liq so'z mosligida esa tarjima ishlaydi va entity tinch qoladi
    assert _light_uz("Team win at Old Trafford &amp; Anfield") == \
        "Team g'alaba at Old Trafford &amp; Anfield"
    # &#39; ichidagi raqam/harf iboralarga mos kelib, entity'ni yaroqsiz
    # holga ("g&apos;alaba") keltirmasin
    assert _light_uz("Play-off &#39;alaba final") == "Play-off &#39;alaba final"


async def test_summarize_item_unescapes_leaked_entities_before_glossary():
    """Sky/BBC feed'laridan qolgan &#39;/&quot; qatlam tarjimadan OLDIN ochilsin.

    Eski bug: "&#39;alaba" ichidagi bo'lak "win" lug'ati bilan almashtirilib,
    keyin ochilganda "g&apos;alaba" kabi yaroqsiz qoldiq chiqardi.
    """
    item = make(
        "Why play-off win may not send Wales to World Cup",
        "Wales face Norway in the Women&#39;s World Cup play-off final.",
    )
    s = await summarize_item(item)
    assert "g&apos;alaba" not in s and "&#x" not in s and "&#39;" not in s
    assert "g'alaba" in s  # to'g'ri tarjima ochiq apostrof bilan
