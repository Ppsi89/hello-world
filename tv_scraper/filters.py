"""
Filtering module – applies post-scrape filters to listings.

Filters:
  • TV screen size 55–65 inches (detected from title + description via regex)
  • Listing age ≤ 14 days (parsed from the date text shown on the site)
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from tv_scraper.config import MAX_LISTING_AGE_DAYS, TV_SIZE_MAX, TV_SIZE_MIN
from tv_scraper.scraper import Listing

logger = logging.getLogger(__name__)

# ── Size Detection ─────────────────────────────────────────────────────────────
# Matches patterns like  "55 Zoll", "65"", "55 inch", "55-Zoll", "55Zoll"
_SIZE_RE = re.compile(
    r"""
    (\d{2})            # two-digit number (screen size)
    \s*[-]?\s*         # optional separator
    (?:Zoll|zoll|inch|Inch|INCH|"|″)  # unit keyword
    """,
    re.VERBOSE,
)


def extract_tv_size(text: str) -> Optional[int]:
    """Return the first TV screen-size (inches) found in *text*, or None."""
    m = _SIZE_RE.search(text)
    return int(m.group(1)) if m else None


def is_size_ok(listing: Listing) -> bool:
    """Return True if the listing's TV size is within the configured range."""
    combined = f"{listing.title} {listing.description}"
    size = extract_tv_size(combined)
    if size is None:
        return False
    return TV_SIZE_MIN <= size <= TV_SIZE_MAX


# ── Date Detection ─────────────────────────────────────────────────────────────
# Kleinanzeigen shows dates like "Heute, 14:02", "Gestern, 09:30",
# "17.03.2025" or relative like "17.03.".
_DATE_FORMATS = ["%d.%m.%Y", "%d.%m."]

_RELATIVE_WORDS = {
    "heute": 0,
    "gestern": 1,
}


def _parse_date(text: str) -> Optional[datetime]:
    """Best-effort parse of the date string shown on kleinanzeigen.de."""
    lower = text.strip().lower()

    # Relative dates
    for word, days_ago in _RELATIVE_WORDS.items():
        if word in lower:
            return datetime.now() - timedelta(days=days_ago)

    # Absolute dates
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(text.strip(), fmt)
            # If year is missing (format %d.%m.) assume current year
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            return dt
        except ValueError:
            continue

    return None


def is_recent(listing: Listing) -> bool:
    """Return True if the listing was posted within the last N days."""
    dt = _parse_date(listing.date_text)
    if dt is None:
        # Be lenient: if we can't parse the date, include the listing
        logger.debug("Could not parse date '%s' – including listing.", listing.date_text)
        return True
    cutoff = datetime.now() - timedelta(days=MAX_LISTING_AGE_DAYS)
    return dt >= cutoff


# ── Combined Filter ────────────────────────────────────────────────────────────
def filter_listings(listings: list[Listing]) -> list[Listing]:
    """Apply all filters and return only matching listings."""
    results: list[Listing] = []
    for listing in listings:
        if not is_size_ok(listing):
            logger.debug("Filtered out (size): %s", listing.title)
            continue
        if not is_recent(listing):
            logger.debug("Filtered out (date): %s", listing.title)
            continue
        results.append(listing)

    logger.info(
        "Filtering complete: %d / %d listings passed.", len(results), len(listings)
    )
    return results
