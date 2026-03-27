"""
Unit tests for the filters module.
"""

from datetime import datetime, timedelta

import pytest

from tv_scraper.filters import extract_tv_size, is_recent, is_size_ok
from tv_scraper.scraper import Listing


# ── extract_tv_size ───────────────────────────────────────────────────────────
class TestExtractTvSize:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ('Samsung 55 Zoll 4K', 55),
            ('LG 65" OLED TV', 65),
            ("Sony 55-Zoll UHD", 55),
            ('Fernseher 58 Zoll Smart TV', 58),
            ("TV 60 inch HDR", 60),
            ("55Zoll Samsung", 55),
            ("65″ QLED", 65),
            ("No size mentioned", None),
            ("42 Zoll too small", 42),
            ("", None),
        ],
    )
    def test_sizes(self, text: str, expected):
        assert extract_tv_size(text) == expected


# ── is_size_ok ────────────────────────────────────────────────────────────────
class TestIsSizeOk:
    def test_within_range(self):
        listing = Listing(title="Samsung 55 Zoll 4K", description="Great TV")
        assert is_size_ok(listing) is True

    def test_above_range(self):
        listing = Listing(title="Samsung 75 Zoll 4K", description="")
        assert is_size_ok(listing) is False

    def test_below_range(self):
        listing = Listing(title="Samsung 42 Zoll", description="")
        assert is_size_ok(listing) is False

    def test_size_in_description(self):
        listing = Listing(title="Fernseher", description="Es ist ein 58 Zoll TV")
        assert is_size_ok(listing) is True

    def test_no_size(self):
        listing = Listing(title="Fernseher", description="Good TV")
        assert is_size_ok(listing) is False


# ── is_recent ─────────────────────────────────────────────────────────────────
class TestIsRecent:
    def test_heute(self):
        listing = Listing(date_text="Heute, 14:02")
        assert is_recent(listing) is True

    def test_gestern(self):
        listing = Listing(date_text="Gestern, 09:30")
        assert is_recent(listing) is True

    def test_recent_absolute_date(self):
        recent = (datetime.now() - timedelta(days=3)).strftime("%d.%m.%Y")
        listing = Listing(date_text=recent)
        assert is_recent(listing) is True

    def test_old_absolute_date(self):
        old = (datetime.now() - timedelta(days=30)).strftime("%d.%m.%Y")
        listing = Listing(date_text=old)
        assert is_recent(listing) is False

    def test_unparseable_date_included(self):
        listing = Listing(date_text="something weird")
        # unparseable dates are included by default
        assert is_recent(listing) is True
