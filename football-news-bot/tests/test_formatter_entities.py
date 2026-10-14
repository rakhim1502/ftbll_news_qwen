"""Regresiya: Telegram xabarida yaroqsiz qoldiq entity kodlar bo'lmasin.

Eski bug: html.escape(quote=True) apostrofnı '&#x27;' ga aylantirardi va
bu holda chiqqan matnda "&#x" pattern'i qolardi (test 'Yomon pattern: &#x').
"""

from datetime import datetime, timezone

from app.services.news_fetcher import NewsItem, _strip_html
from app.utils.formatter import format_news_message


def make(title, summary="", url="https://example.com/a", source="Sky Sports"):
    return NewsItem(title=title, url=url, summary=summary,
                    published=datetime.now(timezone.utc), source_name=source)


def test_apostrophe_titles_do_not_leave_hex_entities():
    dirty = "Haaland &#x27;s goal &amp; assist \u2014 beat &#39;strong&#39; Liverpool <b>2-1</b>"
    clean = _strip_html(dirty)
    chunks = format_news_message([(make(clean, clean), "Qisqa mazmun.")])
    msg = chunks[0]
    assert "&#x" not in msg, "Yomon pattern: &#x"
    assert "&amp;amp;" not in msg
    # To'g'ri escape saqlanadi:
    assert "&amp;" in msg            # '&' belgisi xavfsiz kodlangan
    assert "<b>" in msg              # format teglari o'rnida turibdi


def test_plain_text_with_ampersand_still_escaped_once():
    chunks = format_news_message([(make("A & B", url="https://e.com/x?1&2"), "Matn")])
    msg = chunks[0]
    assert "A &amp; B" in msg
    assert "x?1&amp;2" in msg
    assert "&#x" not in msg
