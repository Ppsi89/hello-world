"""
Unit tests for the scraper module (parsing helpers).
"""

import pytest

from tv_scraper.scraper import Listing, _parse_price_cents


class TestParsePriceCents:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("249 €", 24900),
            ("1.200 €", 120000),
            ("350 € VB", 35000),
            ("kostenlos", None),
            ("", None),
        ],
    )
    def test_parse(self, text: str, expected):
        assert _parse_price_cents(text) == expected


class TestListingDefaults:
    def test_defaults(self):
        listing = Listing()
        assert listing.title == ""
        assert listing.images == []
        assert listing.price_cents is None
