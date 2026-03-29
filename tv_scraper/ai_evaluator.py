"""
AI Evaluation module – scores listings using the OpenAI API.

Each listing is evaluated on brand reputation, features, condition,
estimated year of manufacture, and the ratio of current price to the
TV's original release price (lower ratio = better deal).
A composite score (0–100) is produced.

When no OpenAI API key is configured the module falls back to a
simple heuristic scorer so the pipeline still works.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from tv_scraper.config import OPENAI_API_KEY, OPENAI_MODEL, TOP_N
from tv_scraper.scraper import Listing

logger = logging.getLogger(__name__)


@dataclass
class ScoredListing:
    listing: Listing
    score: float = 0.0
    summary: str = ""
    features: list[str] = None  # type: ignore[assignment]
    brand: str = ""
    model: str = ""
    year: Optional[int] = None
    release_price_cents: Optional[int] = None

    def __post_init__(self) -> None:
        if self.features is None:
            self.features = []

    @property
    def price_ratio(self) -> Optional[float]:
        """Ratio of current price to release price (None if either is unknown)."""
        if self.listing.price_cents and self.release_price_cents:
            return self.listing.price_cents / self.release_price_cents
        return None


# ── OpenAI-backed scorer ──────────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are a consumer-electronics expert.  Given a second-hand TV listing,
return a JSON object with EXACTLY these fields:
{
  "score": <int 0-100>,
  "summary": "<one-sentence why this is a good or bad deal>",
  "brand": "<brand name or 'Unknown'>",
  "model": "<TV model name or 'Unknown'>",
  "year": <estimated manufacturing year as int or null>,
  "price_on_release": <estimated original retail price in EUR as int or null>,
  "features": ["4K", "OLED", ...]
}
Scoring guidelines (total 100):
  • Brand reputation (Samsung/LG/Sony = high, no-name = low): 0-25
  • Features (4K/OLED/QLED/HDR/HDMI2.1/Smart TV): 0-25
  • Condition (based on description): 0-20
  • Price ratio (current price / estimated price at release – lower = better deal): 0-30
      ratio < 0.20 → 30 pts | < 0.35 → 22 pts | < 0.50 → 15 pts | < 0.65 → 8 pts | else → 3 pts
Return ONLY valid JSON, no markdown fences.
"""


def _score_with_openai(listings: list[Listing]) -> list[ScoredListing]:
    """Score listings using the OpenAI chat completions API."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed – falling back to heuristic.")
        return _score_heuristic(listings)

    client = OpenAI(api_key=OPENAI_API_KEY)
    results: list[ScoredListing] = []

    for listing in listings:
        user_msg = (
            f"Title: {listing.title}\n"
            f"Price: {listing.price}\n"
            f"Description: {listing.description}\n"
            f"Location: {listing.location}\n"
            f"Date: {listing.date_text}\n"
            f"URL: {listing.url}"
        )
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=300,
            )
            raw = resp.choices[0].message.content or "{}"
            data = json.loads(raw)
            price_on_release = data.get("price_on_release")
            release_price_cents = int(price_on_release * 100) if price_on_release else None
            results.append(
                ScoredListing(
                    listing=listing,
                    score=float(data.get("score", 0)),
                    summary=data.get("summary", ""),
                    brand=data.get("brand", ""),
                    model=data.get("model", ""),
                    year=data.get("year"),
                    features=data.get("features", []),
                    release_price_cents=release_price_cents,
                )
            )
        except Exception as exc:
            logger.warning("OpenAI scoring failed for '%s': %s", listing.title, exc)
            results.append(ScoredListing(listing=listing, score=0, summary="AI scoring failed"))

    return results


# ── Heuristic fallback scorer ─────────────────────────────────────────────────
_BRAND_SCORES: dict[str, int] = {
    "samsung": 23,
    "lg": 22,
    "sony": 24,
    "philips": 18,
    "panasonic": 19,
    "hisense": 15,
    "tcl": 14,
    "toshiba": 13,
    "grundig": 12,
    "medion": 10,
    "xiaomi": 14,
}

_FEATURE_KEYWORDS: dict[str, int] = {
    "oled": 8,
    "qled": 7,
    "4k": 5,
    "uhd": 5,
    "hdr": 4,
    "hdmi 2.1": 4,
    "smart tv": 3,
    "smart-tv": 3,
    "dolby": 3,
    "ambilight": 3,
    "120hz": 4,
    "120 hz": 4,
}


def _score_heuristic(listings: list[Listing]) -> list[ScoredListing]:
    """Simple rule-based scorer used when OpenAI is unavailable."""
    results: list[ScoredListing] = []

    for listing in listings:
        text = f"{listing.title} {listing.description}".lower()
        score = 0.0
        features: list[str] = []
        brand = "Unknown"

        # Brand
        for b, pts in _BRAND_SCORES.items():
            if b in text:
                score += pts
                brand = b.title()
                break

        # Features
        for kw, pts in _FEATURE_KEYWORDS.items():
            if kw in text:
                score += pts
                features.append(kw.upper())

        # Condition bonus (listing already filtered for "like new")
        score += 15

        # Price bonus – lower price = better
        if listing.price_cents:
            price_eur = listing.price_cents / 100
            if price_eur <= 250:
                score += 25
            elif price_eur <= 300:
                score += 18
            else:
                score += 10

        score = min(score, 100)

        results.append(
            ScoredListing(
                listing=listing,
                score=score,
                summary=f"Heuristic score based on brand ({brand}), features, and price.",
                brand=brand,
                features=features,
            )
        )

    return results


# ── Public API ─────────────────────────────────────────────────────────────────
def evaluate(listings: list[Listing]) -> list[ScoredListing]:
    """Score all listings and return them sorted best-first."""
    if OPENAI_API_KEY:
        scored = _score_with_openai(listings)
    else:
        logger.info("No OPENAI_API_KEY set – using heuristic scorer.")
        scored = _score_heuristic(listings)

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def top_results(scored: list[ScoredListing], n: int = TOP_N) -> list[ScoredListing]:
    """Return the top-N scored listings."""
    return scored[:n]
