"""
Main entry-point – orchestrates scraping → filtering → CSV export.
"""

import logging

from tv_scraper.cache import is_cache_fresh, load_cache, save_cache
from tv_scraper.export_csv import listings_to_csv
from tv_scraper.filters import filter_listings
from tv_scraper.scraper import Listing, scrape_listings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CSV_OUTPUT = "tv_listings.csv"


def run() -> list[Listing]:
    """Execute the pipeline and return filtered listings."""
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

    logger.info("=== Step 3: Exporting to CSV ===")
    listings_to_csv(filtered, CSV_OUTPUT)
    logger.info("Wrote %d listings to %s", len(filtered), CSV_OUTPUT)

    return filtered


def main() -> None:
    filtered = run()

    print("\n" + "=" * 60)
    print("  TV LISTINGS – SUMMARY")
    print("=" * 60)
    if not filtered:
        print("  No matching listings found.")
    for i, listing in enumerate(filtered, 1):
        print(f"\n  #{i}  {listing.title}")
        print(f"      Price : {listing.price}")
        print(f"      Location: {listing.location}")
        print(f"      Date  : {listing.date_text}")
        print(f"      Link  : {listing.url}")
    print(f"\n  CSV saved to: {CSV_OUTPUT}")
    print()


if __name__ == "__main__":
    main()
