"""
Main entry-point – orchestrates scraping → filtering → AI evaluation → output.
"""

import json
import logging
import sys

from tv_scraper.ai_evaluator import ScoredListing, evaluate, top_results
from tv_scraper.cache import cache_timestamp, is_cache_fresh, load_cache, save_cache
from tv_scraper.filters import filter_listings
from tv_scraper.scraper import scrape_listings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _to_dict(sl: ScoredListing) -> dict:
    return {
        "title": sl.listing.title,
        "price": sl.listing.price,
        "score": round(sl.score, 1),
        "summary": sl.summary,
        "brand": sl.brand,
        "year": sl.year,
        "features": sl.features,
        "location": sl.listing.location,
        "date": sl.listing.date_text,
        "url": sl.listing.url,
    }


def run() -> list[dict]:
    """Execute the full pipeline and return results as dicts."""
    logger.info("=== Step 1: Scraping listings ===")
    if is_cache_fresh():
        raw = load_cache()
        logger.info("Loaded %d listings from cache.", len(raw))
    else:
        raw = scrape_listings()
        save_cache(raw)

    logger.info("=== Step 2: Filtering listings ===")
    filtered = filter_listings(raw)

    if not filtered:
        logger.warning("No listings matched the filters.")
        return []

    logger.info("=== Step 3: AI evaluation ===")
    scored = evaluate(filtered)
    best = top_results(scored)

    results = [_to_dict(s) for s in best]
    return results


def main() -> None:
    results = run()

    # ── JSON output ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  TOP TV DEALS – JSON")
    print("=" * 60)
    print(json.dumps(results, indent=2, ensure_ascii=False))

    # ── Readable console output ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  TOP TV DEALS – SUMMARY")
    print("=" * 60)
    if not results:
        print("  No matching listings found.")
    for i, r in enumerate(results, 1):
        print(f"\n  #{i}  {r['title']}")
        print(f"      Price : {r['price']}")
        print(f"      Score : {r['score']}/100")
        print(f"      Brand : {r['brand']}")
        print(f"      Features: {', '.join(r['features']) if r['features'] else '–'}")
        print(f"      Summary: {r['summary']}")
        print(f"      Link  : {r['url']}")
    print()


if __name__ == "__main__":
    main()
