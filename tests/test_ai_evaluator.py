"""
Unit tests for the AI evaluator module (heuristic path).
"""

import pytest

from tv_scraper.ai_evaluator import ScoredListing, evaluate, top_results
from tv_scraper.scraper import Listing


def _make_listing(**kwargs) -> Listing:
    defaults = {
        "title": "TV",
        "price": "250 €",
        "price_cents": 25000,
        "description": "",
        "location": "Berlin",
        "date_text": "Heute",
        "url": "https://example.com/1",
    }
    defaults.update(kwargs)
    return Listing(**defaults)


class TestHeuristicScorer:
    def test_known_brand_scores_higher(self):
        samsung = _make_listing(title="Samsung 55 Zoll 4K UHD")
        noname = _make_listing(title="Noname 55 Zoll TV")
        results = evaluate([samsung, noname])
        assert results[0].brand == "Samsung"
        assert results[0].score > results[1].score

    def test_features_increase_score(self):
        fancy = _make_listing(title="LG 55 Zoll OLED 4K HDR Smart TV")
        basic = _make_listing(title="LG 55 Zoll TV")
        results = evaluate([fancy, basic])
        assert results[0].score > results[1].score

    def test_lower_price_scores_higher(self):
        cheap = _make_listing(title="Samsung 55 Zoll 4K", price="220 €", price_cents=22000)
        expensive = _make_listing(title="Samsung 55 Zoll 4K", price="340 €", price_cents=34000)
        results = evaluate([cheap, expensive])
        assert results[0].listing.price_cents == 22000

    def test_top_results_limits(self):
        listings = [_make_listing(title=f"TV {i}") for i in range(10)]
        scored = evaluate(listings)
        top = top_results(scored, n=3)
        assert len(top) == 3


class TestScoredListingDefaults:
    def test_features_defaults_to_list(self):
        sl = ScoredListing(listing=_make_listing())
        assert sl.features == []

    def test_score_default(self):
        sl = ScoredListing(listing=_make_listing())
        assert sl.score == 0.0
