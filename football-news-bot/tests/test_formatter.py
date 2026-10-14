"""formatter: HTML escape va xabar uzunligi testlari."""

from datetime import datetime, timezone

from app.services.news_fetcher import NewsItem
from app.utils.formatter import (
    escape_html,
    format_news_message,
    format_no_news,
)
from app.config import TELEGRAM_MAX_LEN


def make(title, url="https://example.com/a", source="BBC Sport"):
    return NewsItem(
        title=title,
        url=url,
        summary="",
        published=datetime.now(timezone.utc),
        source_name=source,
    )


def test_escape_html_special_chars():
    raw = 'Tom & Jerry <script>alert("x")</script>'
    esc = escape_html(raw)
    assert "<script>" not in esc
    assert "&lt;script&gt;" in esc
    assert "&amp;" in esc
    # Yaroqsiz qoldiq entity kodlar bo'lmasligi kerak
    assert "&#x" not in esc.replace("&#x27;", "")  # normal holatda &#x... uchramaydi


def test_message_contains_header_and_link():
    chunks = format_news_message([(make("Real Madrid wins CL"), "Real Madrid g'alaba qozondi.")])
    assert len(chunks) == 1
    msg = chunks[0]
    assert "BUGUNGI FUTBOL YANGILIKLARI" in msg
    assert '<a href="https://example.com/a">' in msg
    assert "Manbani o'qish" in msg


def test_url_with_ampersand_escaped():
    chunks = format_news_message([(make("X", url="https://e.com/a?b=1&c=2"), "Matn")])
    assert "b=1&amp;c=2" in chunks[0]


def test_long_list_split_into_chunks_under_limit():
    pairs = [
        (make(f"Story number {i} with quite a long headline text here",
              url=f"https://example.com/{i}"),
         "Sanoatli uzun mazmun. " * 10)
        for i in range(40)
    ]
    chunks = format_news_message(pairs)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= TELEGRAM_MAX_LEN


def test_empty_returns_no_messages():
    assert format_news_message([]) == []


def test_no_news_message_is_valid_html():
    msg = format_no_news()
    assert "<b>" in msg and "</b>" in msg
