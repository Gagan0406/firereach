"""
FireReach – X/Twitter Signal Extractor
Uses apidojo/tweet-scraper (paid Apify actor) to get real tweets.
Falls back to Tavily site:x.com search on free/unavailable plans.
"""
from __future__ import annotations

from typing import Any

from apify_client import ApifyClient

try:
    from utils.logger import get_logger
except ImportError:
    def get_logger(name):
        class _L:
            def info(self, *a, **k): pass
            def error(self, *a, **k): pass
            def warning(self, *a, **k): pass
        return _L()

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


_SIGNAL_KEYWORDS = {
    "funding":     ["funding", "raised", "series", "investment", "valuation", "IPO"],
    "hiring":      ["hiring", "we're hiring", "join our team", "open roles", "careers", "jobs"],
    "product":     ["launched", "announcing", "new product", "new feature", "now available", "beta", "release"],
    "partnership": ["partnership", "partnering", "collaboration", "deal with", "working with"],
    "growth":      ["milestone", "growth", "expansion", "customers", "revenue", "ARR", "MRR"],
}


def _classify_tweet(text: str) -> list[str]:
    text_lower = text.lower()
    return [cat for cat, kws in _SIGNAL_KEYWORDS.items() if any(kw in text_lower for kw in kws)]


def _extract_twitter_signals_apify(company_name: str, apify_token: str, session_id: str) -> dict[str, Any]:
    """Use apidojo/tweet-scraper (requires paid Apify plan)."""
    logger = get_logger(session_id)
    client = ApifyClient(apify_token)

    run = client.actor("apidojo/tweet-scraper").call(
        run_input={
            "searchTerms": [f"{company_name} funding OR hiring OR launched OR partnership"],
            "maxItems": 20,
            "sort": "Latest",
        },
        timeout_secs=120,
    )

    tweets = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        text = item.get("text") or item.get("full_text") or ""
        if not text or item.get("noResults"):
            continue
        tweets.append({
            "text": text,
            "author": item.get("author", {}).get("userName", "") if isinstance(item.get("author"), dict) else str(item.get("author", "")),
            "created_at": item.get("createdAt") or item.get("created_at", ""),
            "likes": item.get("likeCount") or item.get("favorite_count", 0),
            "retweets": item.get("retweetCount") or item.get("retweet_count", 0),
        })

    logger.info("twitter_apify_success", tweets=len(tweets))
    return _build_signal_dict(tweets, source="apidojo/tweet-scraper")


def _extract_twitter_signals_tavily(company_name: str, tavily_key: str, session_id: str) -> dict[str, Any]:
    """Fallback: search X.com via Tavily for company announcements."""
    logger = get_logger(session_id)
    client = TavilyClient(api_key=tavily_key)

    queries = [
        f"site:x.com {company_name} funding OR raised OR series",
        f"site:x.com {company_name} hiring OR launched OR partnership",
    ]

    tweets = []
    for query in queries:
        try:
            results = client.search(query=query, search_depth="basic", max_results=5)
            for r in results.get("results", []):
                text = f"{r.get('title', '')} — {r.get('content', '')}"
                if text.strip():
                    tweets.append({
                        "text": text[:300],
                        "author": "",
                        "created_at": "",
                        "likes": 0,
                        "retweets": 0,
                    })
        except Exception as e:
            logger.warning("tavily_twitter_query_failed", query=query, error=str(e))

    logger.info("twitter_tavily_fallback_success", tweets=len(tweets))
    return _build_signal_dict(tweets, source="tavily-x.com")


def _build_signal_dict(tweets: list[dict], source: str) -> dict[str, Any]:
    """Build structured signal output from raw tweet list."""
    result = {
        "source": source,
        "total_mentions": len(tweets),
        "funding_tweets": [],
        "hiring_tweets": [],
        "product_tweets": [],
        "partnership_tweets": [],
        "growth_tweets": [],
        "top_tweets": [],
    }

    for tw in tweets:
        text = tw["text"]
        cats = _classify_tweet(text)
        for cat in cats:
            key = f"{cat}_tweets"
            if key in result and len(result[key]) < 3:
                result[key].append(text[:250])

    # Top 3 tweets by engagement
    sorted_tweets = sorted(tweets, key=lambda t: t.get("likes", 0) + t.get("retweets", 0), reverse=True)
    result["top_tweets"] = [t["text"][:250] for t in sorted_tweets[:3]]

    return result


def _extract_twitter_signals(company_name: str, apify_token: str, session_id: str) -> dict[str, Any]:
    """
    Try apidojo/tweet-scraper first; fall back to Tavily site:x.com search.
    """
    logger = get_logger(session_id)

    # Try Apify paid actor first
    try:
        result = _extract_twitter_signals_apify(company_name, apify_token, session_id)
        if result.get("total_mentions", 0) > 0:
            return result
        # If we got 0 results (free plan limitation), fall through to Tavily
        logger.warning("twitter_apify_no_results", reason="likely free plan limitation")
    except Exception as e:
        logger.warning("twitter_apify_failed", error=str(e))

    # Fallback: Tavily site:x.com
    try:
        from utils.config import get_settings
        settings = get_settings()
        if TavilyClient and settings.tavily_api_key:
            return _extract_twitter_signals_tavily(company_name, settings.tavily_api_key, session_id)
    except Exception as e:
        logger.error("twitter_tavily_fallback_failed", error=str(e))

    return {"error": "All Twitter extraction methods failed", "total_mentions": 0}


def format_twitter_signals(data: dict[str, Any]) -> list[str]:
    """Convert Twitter signal dict to list of signal strings for LLM."""
    if data.get("error") or not data.get("total_mentions"):
        return []

    signals = []
    source = data.get("source", "X/Twitter")

    if data.get("funding_tweets"):
        signals.append(f"[X/Twitter] Funding mention: {data['funding_tweets'][0]}")

    if data.get("hiring_tweets"):
        signals.append(f"[X/Twitter] Hiring activity: {data['hiring_tweets'][0]}")

    if data.get("product_tweets"):
        signals.append(f"[X/Twitter] Product announcement: {data['product_tweets'][0]}")

    if data.get("partnership_tweets"):
        signals.append(f"[X/Twitter] Partnership signal: {data['partnership_tweets'][0]}")

    if data.get("growth_tweets"):
        signals.append(f"[X/Twitter] Growth signal: {data['growth_tweets'][0]}")

    if data.get("top_tweets") and not signals:
        # If no classified signals, include top tweet
        signals.append(f"[X/Twitter] Recent mention: {data['top_tweets'][0]}")

    return signals
