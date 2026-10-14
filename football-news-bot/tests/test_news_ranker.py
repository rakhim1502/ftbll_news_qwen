"""news_ranker: futbol filtri, dedupe va ballash testlari."""

from datetime import datetime, timedelta, timezone

from app.services.news_fetcher import NewsItem
from app.services.news_ranker import (
    deduplicate,
    is_football,
    rank_news,
    score_item,
)

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
    items = [make(f"Football unique story {i}", f"https://a.com/football/{i}") for i in range(25)]
    top = rank_news(items, max_items=10)
    assert len(top) == 10

    few = [make("Manchester United only story", "https://a.com/football/only")]
    assert len(rank_news(few, min_items=5, max_items=10)) == 1  # sun'iy to'ldirilmaydi


# --- Futbol filtri (is_football / rank_news) --------------------------------

def test_is_football_accepts_url_with_football_segment():
    it = make("Bruno Fernandes: what is wrong?", "https://www.skysports.com/football/news/12040/1")
    assert is_football(it) is True


def test_is_football_rejects_rugby_league_even_with_world_cup():
    # Regressiya: "Rugby League World Cup" futboylar ro'yxatiga kirmasligi kerak
    it = make(
        "England rocked by injury on eve of Rugby League World Cup",
        "https://www.skysports.com/rugby-league/news/12040/1",
    )
    assert is_football(it) is False


def test_is_football_rejects_tennis_golf_nfl_urls():
    for title, url in [
        ("Six Kings Slam tournament postponed", "https://www.skysports.com/tennis/news/12040/2"),
        ("McIlroy reveals viral baggy trousers", "https://www.skysports.com/golf/news/12040/3"),
        ("NFL suspends Rams' Jackson", "https://www.skysports.com/nfl/news/12040/4"),
    ]:
        assert is_football(make(title, url)) is False, title


def test_is_football_accepts_bbc_style_football_title():
    it = make("Real Madrid vs Barcelona preview", "https://www.bbc.co.uk/sport/football/articles/abc")
    assert is_football(it) is True


def test_rank_news_filters_out_non_football():
    football = make(
        "Champions League: Arsenal beat PSG",
        "https://www.bbc.co.uk/sport/football/articles/x1",
    )
    tennis = make(
        "Wimbledon star wins final",
        "https://www.skysports.com/tennis/news/12040/x2",
    )
    top = rank_news([football, tennis], max_items=10)
    assert len(top) == 1
    assert top[0].url == football.url
