"""
Unit tests for the config module.
"""

from tv_scraper.config import build_search_url


class TestBuildSearchUrl:
    def test_page_1(self):
        url = build_search_url(1)
        assert "13599" in url
        assert "preis:200:350" in url
        assert "seite:" not in url

    def test_page_2(self):
        url = build_search_url(2)
        assert "seite:2" in url

    def test_contains_category(self):
        url = build_search_url(1)
        assert "fernseher" in url
        assert "like_new" in url
