#!/usr/bin/env python3
"""RSS manbalarini real internet so'rovlari bilan tekshiruvchi smoke-test.

Ishga tushirish (loyiha ildizidan):
    python scripts/smoke_sources.py

Har bir manba uchun chiqadi:
  [OK]   BBC Sport        -> 12 ta yangi xabar (eng yangisi: 2026-10-14 08:12 UTC)
  [FAIL] Sky Sports       -> HTTP 403 / TimeoutError / ParseError ...

Chiqish kodi: kamida bitta manba OK bo'lsa 0, aks holda 1.
Bu skript pytest testi emas — qo'lda bajariladigan diagnostika vositasi.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Loyiha paketlarini import qilish uchun ildiz papkani sys.path'ga qo'shamiz
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from app.config import HTTP_TIMEOUT_SEC, HTTP_USER_AGENT, RSS_SOURCES  # noqa: E402
from app.services.news_fetcher import NewsItem, fetch_news, parse_feed  # noqa: E402


async def check_source(client: httpx.AsyncClient, source) -> tuple[bool, str]:
    """Bitta manbani tekshiradi. (ok, detail) qaytaradi."""
    try:
        resp = await client.get(source.url, follow_redirects=True)
    except Exception as e:  # noqa: BLE001 - diagnostika: har qanday xatoni ko'rsatish kerak
        return False, f"{type(e).__name__}: {e}"

    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"

    try:
        items = parse_feed(resp.text, source)
    except Exception as e:  # noqa: BLE001
        return False, f"ParseError: {type(e).__name__}: {e}"

    if not items:
        return False, "XML o'qildi, lekin hech qanday <item>/<entry> topilmadi"

    now = datetime.now(timezone.utc)
    fresh = [i for i in items if (now - i.published) <= timedelta(hours=72)]
    latest = max(i.published for i in items)
    return True, (
        f"{len(items)} ta xabar, {len(fresh)} tasi oxirgi 72 soatda; "
        f"eng yangisi: {latest:%Y-%m-%d %H:%M} UTC"
    )


async def main() -> int:
    print(f"Tekshiruv sanasi: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
    print(f"Manbalar soni: {len(RSS_SOURCES)}\n")

    ok_count = 0
    timeout = httpx.Timeout(HTTP_TIMEOUT_SEC, connect=min(HTTP_TIMEOUT_SEC, 8.0))
    async with httpx.AsyncClient(
        headers={"User-Agent": HTTP_USER_AGENT}, timeout=timeout
    ) as client:
        results = await asyncio.gather(*(check_source(client, s) for s in RSS_SOURCES))

    for source, (ok, detail) in zip(RSS_SOURCES, results):
        status = "[OK]  " if ok else "[FAIL]"
        print(f"{status} {source.name:<30} -> {detail}")
        if ok:
            ok_count += 1

    # Umumiy pipeline sinovi (fetch + parallel + date filter):
    print("\n--- fetch_news() umumiy sinov ---")
    try:
        items: list[NewsItem] = await fetch_news(max_age_hours=36)
        if items:
            print(f"[OK]   Jami {len(items)} ta 'bugungi' xabar yig'ildi.")
            for it in items[:3]:
                print(f"       * {it.title[:70]} ({it.source_name})")
        else:
            print("[WARN] Xabar topilmadi (hozircha yangi nashr yo'q bo'lishi mumkin).")
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] fetch_news(): {type(e).__name__}: {e}")

    print(f"\nXULOSA: {ok_count}/{len(RSS_SOURCES)} manba ishlayapti.")
    return 0 if ok_count >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
