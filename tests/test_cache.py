"""
Unit tests for the CSV cache module.
"""

import csv
import os
import time

import pytest

from tv_scraper.scraper import Listing


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_listing(**kwargs) -> Listing:
    defaults = {
        "title": "Samsung 55 Zoll 4K",
        "price": "250 €",
        "price_cents": 25000,
        "description": "Sehr guter Zustand",
        "location": "Berlin",
        "date_text": "Heute",
        "url": "https://example.com/1",
        "images": ["https://img.example.com/1.jpg"],
    }
    defaults.update(kwargs)
    return Listing(**defaults)


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestSaveAndLoad:
    def test_roundtrip(self, tmp_path, monkeypatch):
        cache_file = str(tmp_path / "cache.csv")
        monkeypatch.setenv("TV_CACHE_FILE", cache_file)

        # Re-import so the module picks up the patched env var
        import importlib
        import tv_scraper.config as cfg
        import tv_scraper.cache as cache_mod
        importlib.reload(cfg)
        importlib.reload(cache_mod)

        listings = [
            _make_listing(title="TV A", price_cents=20000),
            _make_listing(title="TV B", price_cents=None, images=[]),
        ]
        cache_mod.save_cache(listings)
        loaded = cache_mod.load_cache()

        assert len(loaded) == 2
        assert loaded[0].title == "TV A"
        assert loaded[0].price_cents == 20000
        assert loaded[1].title == "TV B"
        assert loaded[1].price_cents is None
        assert loaded[1].images == []

    def test_images_roundtrip(self, tmp_path, monkeypatch):
        cache_file = str(tmp_path / "cache.csv")
        monkeypatch.setenv("TV_CACHE_FILE", cache_file)

        import importlib
        import tv_scraper.config as cfg
        import tv_scraper.cache as cache_mod
        importlib.reload(cfg)
        importlib.reload(cache_mod)

        listing = _make_listing(images=["https://a.com/1.jpg", "https://b.com/2.jpg"])
        cache_mod.save_cache([listing])
        loaded = cache_mod.load_cache()

        assert loaded[0].images == ["https://a.com/1.jpg", "https://b.com/2.jpg"]


class TestCacheFreshness:
    def test_no_file_is_not_fresh(self, tmp_path, monkeypatch):
        cache_file = str(tmp_path / "nonexistent.csv")
        monkeypatch.setenv("TV_CACHE_FILE", cache_file)

        import importlib
        import tv_scraper.config as cfg
        import tv_scraper.cache as cache_mod
        importlib.reload(cfg)
        importlib.reload(cache_mod)

        assert cache_mod.is_cache_fresh() is False

    def test_fresh_file_is_fresh(self, tmp_path, monkeypatch):
        cache_file = str(tmp_path / "cache.csv")
        monkeypatch.setenv("TV_CACHE_FILE", cache_file)
        monkeypatch.setenv("TV_CACHE_TTL", "3600")

        import importlib
        import tv_scraper.config as cfg
        import tv_scraper.cache as cache_mod
        importlib.reload(cfg)
        importlib.reload(cache_mod)

        cache_mod.save_cache([_make_listing()])
        assert cache_mod.is_cache_fresh() is True

    def test_old_file_is_not_fresh(self, tmp_path, monkeypatch):
        cache_file = str(tmp_path / "cache.csv")
        monkeypatch.setenv("TV_CACHE_FILE", cache_file)
        monkeypatch.setenv("TV_CACHE_TTL", "3600")

        import importlib
        import tv_scraper.config as cfg
        import tv_scraper.cache as cache_mod
        importlib.reload(cfg)
        importlib.reload(cache_mod)

        cache_mod.save_cache([_make_listing()])
        # Backdate the file by 2 hours
        old_mtime = time.time() - 7200
        os.utime(cache_file, (old_mtime, old_mtime))

        assert cache_mod.is_cache_fresh() is False

    def test_cache_age_seconds(self, tmp_path, monkeypatch):
        cache_file = str(tmp_path / "cache.csv")
        monkeypatch.setenv("TV_CACHE_FILE", cache_file)

        import importlib
        import tv_scraper.config as cfg
        import tv_scraper.cache as cache_mod
        importlib.reload(cfg)
        importlib.reload(cache_mod)

        assert cache_mod.cache_age_seconds() == float("inf")

        cache_mod.save_cache([_make_listing()])
        age = cache_mod.cache_age_seconds()
        assert 0 <= age < 5  # just written, should be nearly 0


class TestCacheTimestamp:
    def test_empty_when_no_file(self, tmp_path, monkeypatch):
        cache_file = str(tmp_path / "nonexistent.csv")
        monkeypatch.setenv("TV_CACHE_FILE", cache_file)

        import importlib
        import tv_scraper.config as cfg
        import tv_scraper.cache as cache_mod
        importlib.reload(cfg)
        importlib.reload(cache_mod)

        assert cache_mod.cache_timestamp() == ""

    def test_returns_string_after_save(self, tmp_path, monkeypatch):
        cache_file = str(tmp_path / "cache.csv")
        monkeypatch.setenv("TV_CACHE_FILE", cache_file)

        import importlib
        import tv_scraper.config as cfg
        import tv_scraper.cache as cache_mod
        importlib.reload(cfg)
        importlib.reload(cache_mod)

        cache_mod.save_cache([_make_listing()])
        ts = cache_mod.cache_timestamp()
        assert ts != ""
        # Should look like "YYYY-MM-DD HH:MM:SS"
        assert len(ts) == 19
