"""Regresiya: Telegram xabarida yaroqsiz qoldiq entity kodlar bo'lmasin.

Eski bug: html.escape(quote=True) apostrofnı '&#x27;' ga aylantirardi va
bu holda chiqqan matnda "&#x" pattern'i qolardi (test 'Yomon pattern: &#x').
"""

from datetime import datetime, timezone

from app.services.news_fetcher import NewsItem, _strip_html
from app.utils.formatter import escape_html, format_news_message


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


def test_escape_html_preserves_valid_amp_entity():
    """Translatordan chiqqan `&amp;` qo'shlab escape bo'lib &amp;amp; bolmasin."""
    assert escape_html("Haaland &amp; Foden") == "Haaland &amp; Foden"
    # yolg'iz & hali ham xavfsiz escape qilinadi
    assert escape_html("Tom & Jerry") == "Tom &amp; Jerry"
    # noma'lum entity zararsizlantiriladi
    assert escape_html("&#39;") == "&amp;#39;"
    # XSS himoyasi saqlanadi
    assert "<script>" not in escape_html("<script>alert(1)</script>")


def test_pipeline_no_double_escape_and_no_junk_entities():
    """To'liq zanjir: RSS -> filtr -> saralash -> mazmun -> format.
    Yakuniy HTML'da &#x qoldig'i va &amp;amp; double-escape bo'lmasligi kerak."""
    import asyncio as _aio
    from datetime import datetime, timedelta, timezone
    from app.config import RSS_SOURCES
    from app.services.news_fetcher import parse_feed
    from app.services.news_ranker import rank_news, is_football
    from app.services.translator import summarize_items

    now = datetime.now(timezone.utc)
    def pub(h): return (now - timedelta(hours=h)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    rss = f"""<?xml version="1.0"?><rss><channel>
    <item><title>Haaland &amp; Foden shine</title>
    <link>https://bbc.co.uk/sport/1?a=1&amp;b=2</link>
    <pubDate>{pub(2)}</pubDate>
    <description>Haaland scored twice.</description></item>
    </channel></rss>"""
    items = [i for i in parse_feed(rss, RSS_SOURCES[0]) if is_football(i)]
    pairs = _aio.run(summarize_items(rank_news(items)))
    full = "\n".join(format_news_message(pairs))
    assert "&#x" not in full
    assert "&amp;amp;" not in full
    assert "Haaland &amp; Foden" in full
    assert "?a=1&amp;b=2" in full  # URL dagi & bir marta escape
