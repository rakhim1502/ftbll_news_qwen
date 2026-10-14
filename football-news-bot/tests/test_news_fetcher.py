"""news_fetcher.parse_feed uchun unit testlar (tarmoqsiz, statik XML bilan)."""

from datetime import timezone

from app.config import RssSource
from app.services.news_fetcher import parse_feed

SOURCE = RssSource("Test Source", "https://example.com/rss", "main")

RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Football Test</title>
  <item>
    <title>Real Madrid &lt;star&gt; signs new striker</title>
    <link>https://example.com/article-1</link>
    <pubDate>Wed, 14 Oct 2026 10:00:00 GMT</pubDate>
    <description>&lt;p&gt;The club confirms the deal.&lt;/p&gt;</description>
  </item>
  <item>
    <title>No date item</title>
    <link>https://example.com/article-2</link>
    <description>Sanasi yo'q — chiqarilmasligi kerak</description>
  </item>
  <item>
    <title>Bad link item</title>
    <link>not-a-url</link>
    <pubDate>Wed, 14 Oct 2026 09:00:00 GMT</pubDate>
  </item>
</channel></rss>"""

ATOM_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Champions League draw</title>
    <link href="https://example.com/atom-1"/>
    <updated>2026-10-14T08:00:00Z</updated>
    <summary>Group stage draw held in Nyon.</summary>
  </entry>
</feed>"""


def test_rss_parsing_basic():
    items = parse_feed(RSS_XML, SOURCE)
    assert len(items) == 1  # sanasiz va URL'siz yozuvlar chiqarib tashlanadi
    it = items[0]
    # Xavfsizlik: sarlavhadagi teg ko'rinishidagi matn ham tozalanadi,
    # & escape'i esa ochiladi (formatter keyin qayta escape qiladi)
    assert it.title == "Real Madrid signs new striker"
    assert "<star>" not in it.title
    assert it.url == "https://example.com/article-1"
    assert "confirms the deal" in it.summary
    assert "<p>" not in it.summary  # HTML teglar olib tashlangan
    assert it.published.tzinfo == timezone.utc
    assert it.source_name == "Test Source"


def test_atom_parsing():
    items = parse_feed(ATOM_XML, SOURCE)
    assert len(items) == 1
    assert items[0].url == "https://example.com/atom-1"
    assert items[0].published.year == 2026


def test_invalid_xml_no_crash():
    assert parse_feed("<broken><xml>", SOURCE) == []
    assert parse_feed("", SOURCE) == []


def test_double_escaped_entities_cleaned():
    xml = """<rss><channel><item>
      <title>Team A &amp;amp; Team B</title>
      <link>https://example.com/x</link>
      <pubDate>Wed, 14 Oct 2026 10:00:00 GMT</pubDate>
      <description>&amp;#x27;Quote&amp;#x27; and &amp;amp; sign</description>
    </item></channel></rss>"""
    items = parse_feed(xml, SOURCE)
    assert len(items) == 1
    # Qoldiq entity kodlar (&#x ...; kabi) qolmasligi kerak
    assert "&#x" not in items[0].summary
    assert "&amp;" not in items[0].summary
