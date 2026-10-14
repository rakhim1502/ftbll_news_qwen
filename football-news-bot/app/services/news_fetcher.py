"""Yangiliklarni RSS manbalaridan yig'ib keluvchi servis.

Minimal MVP versiyasi:
- Barcha manbalarga PARALLEL so'rov yuboradi (httpx.AsyncClient).
- Har bir manba uchun timeout va xato holatini alohida ushlaydi —
  bitta manba ishlamasa, bot to'xtab qolmaydi.
- RSS/Atom XMLni standart kutubxona (xml.etree) bilan oddiy parse qiladi
  (keraksiz qo'shimcha kutubxonalarsiz).
- Faqat sanasi ma'lum va "bugungi" (NEWS_MAX_AGE_HICHOURS oynasidagi)
  xabarlarni qaytaradi.
"""

from __future__ import annotations

import asyncio
import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx

from app.config import HTTP_TIMEOUT_SEC, HTTP_USER_AGENT, RSS_SOURCES, RssSource

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    title: str
    url: str
    summary: str          # RSS'dagi qisqa tavsif (HTML tozalanagan)
    published: datetime   # UTC
    source_name: str


_ENTITY_RE = re.compile(r"&(?:(#[0-9]+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);?)")


def _strip_html(text: str) -> str:
    """HTML teglarini va barcha entity kodlarini sof matnga aylantiradi.

    Matn XML parse'idan keyin allaqachon bitta entity qatlamdan ochilgan
    bo'ladi. Lekin ba'zi manbalar (The Guardian CDATA, Sky Sports HTML
    tavsifi) qo'shimcha escape qatlamini saqlaydi (&amp;#x27; kabi).
    Shu sababli entity ochishni *takror-takror* bajaramiz — to yakuniy
        qatorda hech qanday "&..." ko'rinishidagi kod qolmaguncha.
    Natijada NewsItem matnlari 100% sof (plain) matn bo'ladi; formatter
    buni Telegram uchun bir marta escape qiladi.
    """
    text = re.sub(r"<[^>]+>", " ", text or "")
    # Cheklangan iteratsiyalar bilan to'liq unescape (xavfsizlik uchun max 5):
    for _ in range(5):
        if not _ENTITY_RE.search(text):
            break
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    # Baribir qolib ketgan noto'g'ri entity'larni (masalan, "&#x" uzilgan)
    # xavfsiz o'chiramiz:
    text = re.sub(r"&(#x?[0-9A-Fa-f]*;?|amp;?|lt;?|gt;?|quot;?|apos;?|nbsp;?)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(raw: str | None) -> datetime | None:
    """RSS pubDate / Atom updated ni UTC datetime'ga aylantiradi."""
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)  # RFC 2822: 'Wed, 14 Oct 2026 15:59:00 BST'
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))  # ISO 8601
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _first_text(el: ET.Element, *tags: str) -> str | None:
    """Berilgan teglardan birinchisini matnini qaytaradi (namespace-siz izlash)."""
    for tag in tags:
        found = el.find(tag)
        if found is None:  # atom namespace ehtimoli
            found = next((c for c in el if c.tag.endswith(f"}}{tag}") or c.tag == tag), None)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
    return None


def _extract_link(item: ET.Element) -> str | None:
    # RSS: <link>text</link>; Atom: <link href="..."/>
    link_el = item.find("link")
    if link_el is None:
        link_el = next((c for c in item if c.tag.endswith("}link")), None)
    if link_el is None:
        return None
    if (link_el.text or "").strip():
        return link_el.text.strip()
    return link_el.get("href")


def parse_feed(xml_text: str, source: RssSource) -> list[NewsItem]:
    """RSS 2.0 va Atom feed'lardan NewsItem ro'yxatini yasaydi."""
    items: list[NewsItem] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("XML parse xatosi (%s): %s", source.name, exc)
        return items

    entries = root.findall(".//item")  # RSS 2.0
    if not entries:
        entries = [el for el in root.iter() if el.tag.endswith("}entry") or el.tag == "entry"]  # Atom

    for el in entries:
        title = _strip_html(_first_text(el, "title") or "")
        url = _extract_link(el)
        published = _parse_date(_first_text(el, "pubDate", "published", "updated", "date"))
        summary = _strip_html(_first_text(el, "description", "summary", "content") or "")

        if not title or not url or not url.startswith(("http://", "https://")):
            continue
        if published is None:
            # Sanasi noma'lum xabarni bugungi yangilik sifatida ko'rsatmaymiz.
            continue

        items.append(NewsItem(title=title, url=url, summary=summary,
                              published=published, source_name=source.name))
    return items


async def _fetch_source(client: httpx.AsyncClient, source: RssSource) -> list[NewsItem]:
    """Bitta manbani og'ir bo'lmagan xatolar bilan qaytaradi (hech qachon raise qilmaydi)."""
    try:
        resp = await client.get(source.url, headers={"User-Agent": HTTP_USER_AGENT})
        resp.raise_for_status()
        return parse_feed(resp.text, source)
    except (httpx.HTTPError, asyncio.TimeoutError) as exc:
        logger.warning("Manba %s (%s) yuklanmadi: %s", source.name, source.url, exc)
        return []


async def fetch_news(max_age_hours: int = 36) -> list[NewsItem]:
    """Barcha manbalardan yangiliklarni parallel yig'adi va yangilarini qaytaradi."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC, follow_redirects=True) as client:
        results = await asyncio.gather(*(_fetch_source(client, s) for s in RSS_SOURCES))

    fresh: list[NewsItem] = []
    for items in results:
        fresh += [it for it in items if it.published >= cutoff]

    logger.info("Yig'ildi: %s ta yangi xabar (cutoff: %s)", len(fresh), cutoff.isoformat())
    return fresh
