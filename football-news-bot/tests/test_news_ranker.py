"""news_ranker: dedupe va ballash testlari."""

from datetime import datetime, timedelta, timezone

from app.services.news_fetcher import NewsItem
from app.services.news_ranker import deduplicate, rank_news, score_item

NOW = datetime.now(timezone.utc)


def make(title, url, hours_ago=1, summary="", source="BBC Sport"):
    return NewsItem(
        title=title,
        url=url,
        summary=summary,
        published=NOW - timedelta(hours=hours_ago),
        source_name=source,
    )


def test_dedupe_same_url():
    items = [make("A", "https://e.com/1"), make("A updated", "https://e.com/1?utm=x")]
    assert len(deduplicate(items)) == 1


def test_dedupe_similar_titles():
    items = [
        make("Mbappe signs for Real Madrid", "https://a.com/1"),
        make("Mbappé signs for Real Madrid!", "https://b.com/2"),  # deyarli bir xil sarlavha
    ]
    assert len(deduplicate(items)) == 1


def test_different_news_kept():
    items = [make("News one", "https://a.com/1"), make("News two", "https://a.com/2")]
    assert len(deduplicate(items)) == 2


def test_recency_scores_higher():
    fresh = make("Match report", "https://a.com/1", hours_ago=1)
    old = make("Match report", "https://a.com/2", hours_ago=30)
    assert score_item(fresh) > score_item(old)


def test_keyword_importance():
    transfer = make("Transfer news: Chelsea agrees deal", "https://a.com/1", summary="Champions League")
    plain = make("Local team prepares for season", "https://a.com/2")
    assert score_item(transfer) > score_item(plain)


def test_rank_caps_at_max_and_no_padding():
    items = [make(f"Unique story {i}", f"https://a.com/{i}") for i in range(25)]
    top = rank_news(items, max_items=10)
    assert len(top) == 10

    few = [make("Only story", "https://a.com/only")]
    assert len(rank_news(few, min_items=5, max_items=10)) == 1  # sun'iy to'ldirilmaydi
