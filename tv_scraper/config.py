"""
Configuration for the Kleinanzeigen TV scraper.
All search parameters can be adjusted here.
"""

import os

# ── Search Parameters ──────────────────────────────────────────────────────────
POSTAL_CODE = "13599"
RADIUS_KM = 30
PRICE_MIN = 100
PRICE_MAX = 350
CONDITION = "like_new"          # maps to "Sehr gut" on the site
CATEGORY_PATH = "s-tv-video/fernseher"
CATEGORY_PARAMS = "c175l3432r50+tv_video.art_s:fernseher+tv_video.condition_s:like_new"

# Base URL template – price is embedded in the path
BASE_URL = (
    "https://www.kleinanzeigen.de/"
    "{category_path}/{postal_code}/preis:{price_min}:{price_max}/"
    "{category_params}"
)

# ── Filtering ──────────────────────────────────────────────────────────────────
TV_SIZE_MIN = 55   # inches
TV_SIZE_MAX = 65   # inches
MAX_LISTING_AGE_DAYS = 14

# ── Scraper Settings ──────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 15          # seconds
REQUEST_DELAY = (1.5, 3.0)    # random delay range between requests
MAX_PAGES = 10                # pagination cap
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ── Cache ──────────────────────────────────────────────────────────────────────
CACHE_FILE = os.environ.get("TV_CACHE_FILE", "tv_listings_cache.csv")
CACHE_TTL_SECONDS = int(os.environ.get("TV_CACHE_TTL", "3600"))  # 1 hour

# ── Output ─────────────────────────────────────────────────────────────────────
CSV_OUTPUT = os.environ.get("TV_CSV_OUTPUT", "tv_listings.csv")


def build_search_url(page: int = 1) -> str:
    """Build the search URL for a given page number."""
    url = BASE_URL.format(
        category_path=CATEGORY_PATH,
        postal_code=POSTAL_CODE,
        price_min=PRICE_MIN,
        price_max=PRICE_MAX,
        category_params=CATEGORY_PARAMS,
    )
    if page > 1:
        # Kleinanzeigen uses /seite:<n>/ for pagination
        url = url.replace(
            f"/{POSTAL_CODE}/",
            f"/{POSTAL_CODE}/seite:{page}/",
        )
    return url
