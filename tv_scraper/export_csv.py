#!/usr/bin/env python3
"""
Utilities to export Listing objects to CSV for manual or AI evaluation.

Fields written:
  - title
  - description
  - brand (best-effort extract or 'Unknown')
  - model (best-effort extract or 'not sure')
  - price (human readable)
  - price_cents (integer, helpful for numeric processing)
  - location
  - date
  - url
  - image_urls (semicolon-separated if multiple)
  - condition (if present on Listing)

Usage:
  from tv_scraper.export_csv import listings_to_csv
  listings_to_csv(listings, "out.csv")

Or run as a module (requires your scraper to provide scrape_all()):
  python -m tv_scraper.export_csv out.csv
"""
from __future__ import annotations

import csv
import re
from typing import Iterable, List

from tv_scraper.scraper import Listing  # expected to be present in your project

# Small brand candidates list to help extract brand names
_BRAND_CANDIDATES: List[str] = [
    "Samsung",
    "LG",
    "Sony",
    "Philips",
    "Panasonic",
    "Hisense",
    "TCL",
    "Toshiba",
    "Grundig",
    "Medion",
    "Xiaomi",
]


def _find_brand(text: str) -> str:
    """Return the first matching brand found in text, or 'Unknown'."""
    if not text:
        return "Unknown"
    low = text.lower()
    for b in _BRAND_CANDIDATES:
        if b.lower() in low:
            return b
    return "Unknown"


def _extract_model(text: str, brand: str | None = None) -> str:
    """
    Try to extract a plausible model token from the text.

    Strategy (simple heuristics):
      - If brand is known and present, take tokens after the brand that look like models
        (contain digits or are uppercase alphanum sequences).
      - Otherwise, search for common model-like patterns (letters+digits, e.g. UE55TU8000).
      - Return 'not sure' when no reasonable candidate is found.
    """
    if not text:
        return "not sure"

    # Prefer looking after the brand occurrence
    if brand and brand != "Unknown":
        bi = text.lower().find(brand.lower())
        if bi != -1:
            following = text[bi + len(brand) :].strip()
            tokens = re.split(r"\s+|[,/()\-]", following)
            model_tokens: List[str] = []
            for t in tokens:
                t = t.strip()
                if not t:
                    continue
                # token with digit is a good sign
                if any(ch.isdigit() for ch in t):
                    model_tokens.append(t)
                # uppercase-ish tokens (e.g., XH95)
                elif re.match(r"^[A-Z0-9]{3,}$", t):
                    model_tokens.append(t)
                if len(model_tokens) >= 2:
                    break
            if model_tokens:
                return " ".join(model_tokens)

    # Generic search for patterns like UE55TU8000, XH950, 55A1
    m = re.search(r"\b([A-Z]{1,4}\d{1,4}[A-Z0-9\-]*)\b", text)
    if m:
        return m.group(1)

    # fallback: token containing digits but avoid returning pure year
    m2 = re.search(r"\b([A-Za-z0-9\-]*\d{2,4}[A-Za-z0-9\-]*)\b", text)
    if m2:
        candidate = m2.group(1)
        if not re.fullmatch(r"\d{4}", candidate):
            return candidate

    return "not sure"


def _normalize_image_urls(value: object) -> str:
    """Normalize image_urls attribute into a semicolon-separated string."""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ";".join(str(x) for x in value if x)
    return str(value)


def listings_to_csv(listings: Iterable[Listing], path: str) -> None:
    """
    Write listings to CSV at `path` with recommended columns.

    The Listing type is expected to have at least the attributes used below:
    title, description, price, price_cents, location, date_text, url, image_urls, condition
    """
    fieldnames = [
        "title",
        "description",
        "brand",
        "model",
        "price",
        "price_cents",
        "location",
        "date",
        "url",
        "image_urls",
        "condition",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in listings:
            # Build searchable text for heuristics
            title = getattr(item, "title", "") or ""
            description = getattr(item, "description", "") or ""
            text = f"{title} {description}".strip()

            # brand and model extraction with fallbacks
            brand = getattr(item, "brand", None) or _find_brand(text)
            model = getattr(item, "model", None) or _extract_model(text, brand)
            if not model or model.lower() in ("unknown", "none"):
                model = "not sure"

            # prepare row
            row = {
                "title": title,
                "description": description,
                "brand": brand or "Unknown",
                "model": model,
                "price": getattr(item, "price", "") or "",
                "price_cents": getattr(item, "price_cents", "") or "",
                "location": getattr(item, "location", "") or "",
                "date": getattr(item, "date_text", "") or "",
                "url": getattr(item, "url", "") or "",
                "image_urls": _normalize_image_urls(getattr(item, "image_urls", "")),
                "condition": getattr(item, "condition", "") or "",
            }
            writer.writerow(row)


# Command-line helper
if __name__ == "__main__":
    import sys

    try:
        from tv_scraper.scraper import scrape_all  # type: ignore
    except Exception:
        scrape_all = None  # keep module usable when scraper isn't available

    if len(sys.argv) < 2:
        print("Usage: python -m tv_scraper.export_csv output.csv")
        raise SystemExit(1)

    out_path = sys.argv[1]

    if scrape_all is None:
        print(
            "Could not import scrape_all() from tv_scraper.scraper. "
            "You can import listings_to_csv and call it with a list of Listing objects."
        )
        raise SystemExit(1)

    listings = list(scrape_all())
    listings_to_csv(listings, out_path)
    print(f"Wrote {len(listings)} listings to {out_path}")