"""
Scraper module – fetches listing data from kleinanzeigen.de.

Uses *requests* + *BeautifulSoup*.  Falls back gracefully on
network or parsing errors so the pipeline never crashes silently.
"""

import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup, Tag

from tv_scraper.config import (
    MAX_PAGES,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    USER_AGENT,
    build_search_url,
)

logger = logging.getLogger(__name__)


# ── Data Model ─────────────────────────────────────────────────────────────────
@dataclass
class Listing:
    title: str = ""
    price: str = ""
    price_cents: Optional[int] = None
    description: str = ""
    location: str = ""
    date_text: str = ""
    url: str = ""
    images: list[str] = field(default_factory=list)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
            "Accept": "text/html,application/xhtml+xml",
        }
    )
    return s


def _fetch_full_description(session: requests.Session, url: str) -> str:
    """Wchodzi w konkretne ogłoszenie i pobiera 100% opisu."""
    try:
        # Dodajemy mały losowy delay, żeby nie zablokowali IP za zbyt szybkie wejścia
        time.sleep(random.uniform(1.0, 2.5)) 
        
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Na kleinanzeigen.de pełny opis jest w elemencie o id "viewad-description-text"
        full_desc_el = soup.select_one("#viewad-description-text")
        if full_desc_el:
            # get_text(separator="\n") zachowa przejrzystość (entery)
            return full_desc_el.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.warning("Nie udało się pobrać pełnego opisu z %s: %s", url, e)
    
    return "" # Jeśli się nie uda, zwraca pusty string

def _parse_price_cents(text: str) -> Optional[int]:
    """Extract price in euro-cents from a string like '249 €' or '1.200 €'."""
    cleaned = text.replace(".", "").replace(",", ".")
    m = re.search(r"([\d.]+)", cleaned)
    if m:
        try:
            return int(float(m.group(1)) * 100)
        except ValueError:
            return None
    return None


def _parse_listing_card(card: Tag, base: str) -> Optional[Listing]:
    """Extract fields from a single search-result card element."""
    listing = Listing()

    # Title + link
    title_el = card.select_one("a.ellipsis")
    if title_el:
        listing.title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        listing.url = href if href.startswith("http") else base + href

    # Price
    price_el = card.select_one("p.aditem-main--middle--price-shipping--price")
    if price_el:
        listing.price = price_el.get_text(strip=True)
        listing.price_cents = _parse_price_cents(listing.price)

    # Description snippet
    desc_el = card.select_one("p.aditem-main--middle--description")
    if desc_el:
        listing.description = desc_el.get_text(" ", strip=True)

    # Location + date
    details_el = card.select_one("div.aditem-main--top--left")
    if details_el:
        listing.location = details_el.get_text(" ", strip=True)

    date_el = card.select_one("div.aditem-main--top--right")
    if date_el:
        listing.date_text = date_el.get_text(strip=True)

    # Images
    img_el = card.select_one("div.imagebox img, img.imagebox")
    if img_el:
        src = img_el.get("src") or img_el.get("data-src") or ""
        if src:
            listing.images.append(src)

    return listing if listing.title else None


# ── Public API ─────────────────────────────────────────────────────────────────
def scrape_listings() -> list[Listing]:
    session = _session()
    all_listings: list[Listing] = []
    base = "https://www.kleinanzeigen.de"

    for page in range(1, MAX_PAGES + 1):
        url = build_search_url(page)
        logger.info("Fetching page %d: %s", page, url)

        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Request failed for page %d: %s", page, exc)
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("article.aditem")

        if not cards:
            logger.info("No more listings found on page %d – stopping.", page)
            break

        for card in cards:
            listing = _parse_listing_card(card, base)
            if listing and listing.url:
                logger.info("Pobieram pełny opis dla: %s", listing.title)
                full_description = _fetch_full_description(session, listing.url)
                
                if full_description:
                    listing.description = full_description
                
                all_listings.append(listing)

        logger.info(
            "Page %d: found %d listings (total so far: %d)",
            page,
            len(cards),
            len(all_listings),
        )

        # Polite delay
        time.sleep(random.uniform(*REQUEST_DELAY))

    logger.info("Scraping complete – %d raw listings collected.", len(all_listings))
    return all_listings