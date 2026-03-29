"""
CSV-based cache for raw scraped listings.

The cache is considered *fresh* if the file was written within the last
CACHE_TTL_SECONDS seconds (default: 3600 = 1 hour).  This prevents
hammering kleinanzeigen.de on repeated runs.

Usage::

    from tv_scraper.cache import is_cache_fresh, load_cache, save_cache

    if is_cache_fresh():
        raw = load_cache()
    else:
        raw = scrape_listings()
        save_cache(raw)
"""

import csv
import logging
import os
import time
from datetime import datetime

from tv_scraper.config import CACHE_FILE, CACHE_TTL_SECONDS
from tv_scraper.scraper import Listing

logger = logging.getLogger(__name__)

_FIELDS = [
    "title",
    "price",
    "price_cents",
    "description",
    "location",
    "date_text",
    "url",
    "images",
]


def cache_age_seconds() -> float:
    """Return the age of the cache file in seconds, or infinity if absent."""
    if not os.path.isfile(CACHE_FILE):
        return float("inf")
    return time.time() - os.path.getmtime(CACHE_FILE)


def is_cache_fresh() -> bool:
    """Return True if the cache file exists and is younger than CACHE_TTL_SECONDS."""
    age = cache_age_seconds()
    if age < CACHE_TTL_SECONDS:
        logger.info(
            "Cache is fresh (%.0f s old, TTL %d s) – skipping scrape.",
            age,
            CACHE_TTL_SECONDS,
        )
        return True
    if age == float("inf"):
        logger.info("No cache file found at '%s' – will scrape.", CACHE_FILE)
    else:
        logger.info(
            "Cache is stale (%.0f s old, TTL %d s) – will re-scrape.",
            age,
            CACHE_TTL_SECONDS,
        )
    return False


def load_cache() -> list[Listing]:
    """Load listings from the CSV cache file."""
    listings: list[Listing] = []
    with open(CACHE_FILE, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            price_cents_raw = row.get("price_cents", "")
            price_cents: int | None = None
            if price_cents_raw:
                try:
                    price_cents = int(price_cents_raw)
                except ValueError:
                    logger.warning(
                        "Ignoring invalid price_cents value '%s' for listing '%s'.",
                        price_cents_raw,
                        row.get("title", "?"),
                    )
            images_raw = row.get("images", "")
            images = [img for img in images_raw.split(";") if img]
            listings.append(
                Listing(
                    title=row.get("title", ""),
                    price=row.get("price", ""),
                    price_cents=price_cents,
                    description=row.get("description", ""),
                    location=row.get("location", ""),
                    date_text=row.get("date_text", ""),
                    url=row.get("url", ""),
                    images=images,
                )
            )
    logger.info("Loaded %d listings from cache ('%s').", len(listings), CACHE_FILE)
    return listings


def save_cache(listings: list[Listing]) -> None:
    """Save listings to the CSV cache file, overwriting any existing file."""
    with open(CACHE_FILE, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELDS)
        writer.writeheader()
        for listing in listings:
            writer.writerow(
                {
                    "title": listing.title,
                    "price": listing.price,
                    "price_cents": listing.price_cents if listing.price_cents is not None else "",
                    "description": listing.description,
                    "location": listing.location,
                    "date_text": listing.date_text,
                    "url": listing.url,
                    "images": ";".join(listing.images),
                }
            )
    logger.info("Saved %d listings to cache ('%s').", len(listings), CACHE_FILE)


def cache_timestamp() -> str:
    """Return a human-readable timestamp for when the cache was last written."""
    if not os.path.isfile(CACHE_FILE):
        return ""
    mtime = os.path.getmtime(CACHE_FILE)
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
