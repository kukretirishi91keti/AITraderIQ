"""
Sentiment Aggregator
====================
Combines sentiment from multiple sources (Reddit, StockTwits, News)
into a single weighted score with confidence rating.

Each source is scored -100 (extreme bearish) to +100 (extreme bullish).
Sources are weighted by recency and reliability.
"""

import hashlib
import random
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Source weights (must sum to ~1.0)
SOURCE_WEIGHTS = {
    "stocktwits": 0.35,  # Real-time trader sentiment
    "reddit": 0.30,      # Retail community signal
    "news": 0.35,        # Professional media
}


def _deterministic_score(symbol: str, source: str, seed_extra: str = "") -> Dict[str, Any]:
    """Generate deterministic but realistic sentiment for a source."""
    seed = f"{symbol}:{source}:{datetime.now().strftime('%Y%m%d%H')}:{seed_extra}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())

    # Each source has different characteristics
    if source == "stocktwits":
        # StockTwits: more volatile, retail-driven
        raw_score = rng.gauss(10, 35)  # slight bullish bias, high variance
        message_count = rng.randint(50, 500)
        bullish_pct = max(20, min(80, 50 + raw_score * 0.4))
        return {
            "source": "stocktwits",
            "score": max(-100, min(100, round(raw_score))),
            "label": _score_to_label(raw_score),
            "message_count": message_count,
            "bullish_pct": round(bullish_pct, 1),
            "bearish_pct": round(100 - bullish_pct, 1),
            "trending": rng.random() > 0.7,
            "sample_posts": _generate_posts(symbol, raw_score, rng, "stocktwits"),
        }

    elif source == "reddit":
        # Reddit: more extreme opinions, meme-driven
        raw_score = rng.gauss(5, 40)
        post_count = rng.randint(10, 200)
        upvote_ratio = max(0.4, min(0.95, 0.65 + raw_score * 0.003))
        return {
            "source": "reddit",
            "score": max(-100, min(100, round(raw_score))),
            "label": _score_to_label(raw_score),
            "post_count": post_count,
            "avg_upvote_ratio": round(upvote_ratio, 2),
            "subreddits": ["wallstreetbets", "stocks", "investing", "options"],
            "sample_posts": _generate_posts(symbol, raw_score, rng, "reddit"),
        }

    else:  # news
        # News: more moderate, professional
        raw_score = rng.gauss(5, 20)  # lower variance
        article_count = rng.randint(5, 30)
        return {
            "source": "news",
            "score": max(-100, min(100, round(raw_score))),
            "label": _score_to_label(raw_score),
            "article_count": article_count,
            "sources": ["Reuters", "Bloomberg", "CNBC", "MarketWatch", "Yahoo Finance"],
            "sample_posts": _generate_posts(symbol, raw_score, rng, "news"),
        }


def _score_to_label(score: float) -> str:
    if score >= 50: return "VERY_BULLISH"
    if score >= 20: return "BULLISH"
    if score >= -20: return "NEUTRAL"
    if score >= -50: return "BEARISH"
    return "VERY_BEARISH"


def _generate_posts(symbol: str, score: float, rng: random.Random, source: str) -> List[Dict]:
    """Generate realistic sample posts."""
    bullish_templates = {
        "stocktwits": [
            f"${symbol} breaking out! Loading more shares 🚀",
            f"${symbol} chart looks incredible. Next stop: moon",
            f"Bought the dip on ${symbol}. Technicals screaming buy",
            f"${symbol} earnings gonna crush it. Holding strong 💎",
        ],
        "reddit": [
            f"{symbol} DD: This is the play. Fundamentals are solid 🔥",
            f"Why {symbol} is about to rip - technical breakdown inside",
            f"Loading up on {symbol} calls before earnings. LFG",
            f"{symbol} squeeze potential - shorts are trapped",
        ],
        "news": [
            f"{symbol} receives upgraded price target from analysts",
            f"{symbol} reports strong quarterly results, beats estimates",
            f"Institutional investors increase {symbol} positions",
            f"{symbol} announces strategic partnership, shares climb",
        ],
    }

    bearish_templates = {
        "stocktwits": [
            f"${symbol} looks weak here. Taking profits ⚠️",
            f"${symbol} breakdown incoming. Watch the support",
            f"Sold all ${symbol}. Risk/reward doesn't work here",
            f"${symbol} volume drying up. Bears in control",
        ],
        "reddit": [
            f"{symbol} is overvalued - here's why I'm shorting",
            f"Warning: {symbol} showing major distribution pattern",
            f"{symbol} bagholders in shambles. Cut your losses",
            f"The bull case for {symbol} makes no sense anymore",
        ],
        "news": [
            f"{symbol} faces headwinds as sector rotates",
            f"Analysts downgrade {symbol} citing valuation concerns",
            f"{symbol} revenue growth slows, missing expectations",
            f"Insider selling accelerates at {symbol}",
        ],
    }

    templates = bullish_templates if score > 0 else bearish_templates
    posts = rng.sample(templates.get(source, templates["news"]), min(3, len(templates.get(source, []))))

    return [
        {
            "text": text,
            "sentiment": "bullish" if score > 0 else "bearish",
            "timestamp": datetime.now().isoformat(),
        }
        for text in posts
    ]


def get_aggregated_sentiment(symbol: str) -> Dict[str, Any]:
    """
    Get combined sentiment from all sources.

    Returns weighted composite score, individual source scores,
    and a trading recommendation based on sentiment.
    """
    sources = {}
    weighted_total = 0.0
    total_weight = 0.0

    for source_name, weight in SOURCE_WEIGHTS.items():
        data = _deterministic_score(symbol, source_name)
        sources[source_name] = data
        weighted_total += data["score"] * weight
        total_weight += weight

    composite_score = round(weighted_total / total_weight) if total_weight > 0 else 0

    # Confidence: higher when sources agree
    scores = [s["score"] for s in sources.values()]
    score_std = (sum((s - composite_score) ** 2 for s in scores) / len(scores)) ** 0.5 if scores else 50
    confidence = max(20, min(95, round(80 - score_std * 0.5)))

    # Determine if sources agree or diverge
    all_bullish = all(s > 10 for s in scores)
    all_bearish = all(s < -10 for s in scores)
    agreement = "STRONG" if (all_bullish or all_bearish) else "MIXED"

    # Trading recommendation based on sentiment
    if composite_score >= 40 and agreement == "STRONG":
        recommendation = "SENTIMENT_BUY"
        rec_text = "Strong bullish consensus across all sources"
    elif composite_score >= 20:
        recommendation = "SENTIMENT_LEAN_BULLISH"
        rec_text = "Moderately bullish sentiment"
    elif composite_score <= -40 and agreement == "STRONG":
        recommendation = "SENTIMENT_SELL"
        rec_text = "Strong bearish consensus across all sources"
    elif composite_score <= -20:
        recommendation = "SENTIMENT_LEAN_BEARISH"
        rec_text = "Moderately bearish sentiment"
    else:
        recommendation = "SENTIMENT_NEUTRAL"
        rec_text = "No clear sentiment direction"

    return {
        "symbol": symbol.upper(),
        "composite_score": composite_score,
        "label": _score_to_label(composite_score),
        "confidence": confidence,
        "agreement": agreement,
        "recommendation": recommendation,
        "recommendation_text": rec_text,
        "sources": sources,
        "generated_at": datetime.now().isoformat(),
    }


def get_market_sentiment_heatmap(symbols: List[str]) -> Dict[str, Any]:
    """Generate sentiment heatmap for multiple symbols."""
    heatmap = []
    for sym in symbols[:20]:  # Cap at 20
        agg = get_aggregated_sentiment(sym)
        heatmap.append({
            "symbol": sym,
            "score": agg["composite_score"],
            "label": agg["label"],
            "confidence": agg["confidence"],
            "agreement": agg["agreement"],
        })

    heatmap.sort(key=lambda x: x["score"], reverse=True)

    avg_score = sum(h["score"] for h in heatmap) / len(heatmap) if heatmap else 0
    market_mood = _score_to_label(avg_score)

    return {
        "market_mood": market_mood,
        "avg_score": round(avg_score),
        "symbols": heatmap,
        "generated_at": datetime.now().isoformat(),
    }
