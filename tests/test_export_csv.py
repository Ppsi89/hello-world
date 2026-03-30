"""
Unit tests for the CSV export module.
"""

import csv

import pytest

from tv_scraper.export_csv import (
    _clean_whitespace,
    _find_brand,
    _extract_model,
    _normalize_image_urls,
    listings_to_csv,
)
from tv_scraper.scraper import Listing


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_listing(**kwargs) -> Listing:
    defaults = {
        "title": "Samsung 55 Zoll 4K TV",
        "price": "250 €",
        "price_cents": 25000,
        "description": "Sehr guter Zustand, kaum benutzt",
        "location": "10585 Charlottenburg (6 km)",
        "date_text": "Heute, 14:02",
        "url": "https://www.kleinanzeigen.de/s-anzeige/test/123-175-3347",
        "images": ["https://img.example.com/1.jpg"],
    }
    defaults.update(kwargs)
    return Listing(**defaults)


# ── Tests: CSV format ─────────────────────────────────────────────────────────

class TestCsvFormat:
    def test_uses_semicolon_delimiter(self, tmp_path):
        path = str(tmp_path / "out.csv")
        listings_to_csv([_make_listing()], path)

        with open(path, encoding="utf-8-sig") as f:
            first_line = f.readline().strip()

        # Header fields must be separated by semicolons
        assert ";" in first_line
        assert first_line.startswith("title;")

    def test_utf8_bom_encoding(self, tmp_path):
        path = str(tmp_path / "out.csv")
        listings_to_csv([_make_listing()], path)

        with open(path, "rb") as f:
            raw = f.read(3)

        # UTF-8 BOM: EF BB BF
        assert raw == b"\xef\xbb\xbf"

    def test_special_characters_preserved(self, tmp_path):
        path = str(tmp_path / "out.csv")
        listing = _make_listing(
            title="Umzug → alles muss weg",
            description="Hisense 55″ TV – Top Zustand, 300 €",
        )
        listings_to_csv([listing], path)

        with open(path, encoding="utf-8-sig") as f:
            content = f.read()

        assert "→" in content
        assert "€" in content
        assert "–" in content
        assert "″" in content


class TestCsvFields:
    def test_header_contains_expected_fields(self, tmp_path):
        path = str(tmp_path / "out.csv")
        listings_to_csv([_make_listing()], path)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            fields = reader.fieldnames

        assert "title" in fields
        assert "brand" in fields
        assert "model" in fields
        assert "size" in fields
        assert "date" in fields
        assert "location" in fields
        assert "price" in fields

    def test_condition_field_removed(self, tmp_path):
        path = str(tmp_path / "out.csv")
        listings_to_csv([_make_listing()], path)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            fields = reader.fieldnames

        assert "condition" not in fields

    def test_size_extracted(self, tmp_path):
        path = str(tmp_path / "out.csv")
        listings_to_csv([_make_listing(title="Samsung 55 Zoll 4K")], path)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            row = next(reader)

        assert row["size"] == '55"'

    def test_size_empty_when_not_found(self, tmp_path):
        path = str(tmp_path / "out.csv")
        listings_to_csv([_make_listing(title="Fernseher zu verkaufen", description="Guter Zustand")], path)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            row = next(reader)

        assert row["size"] == ""

    def test_date_present_in_output(self, tmp_path):
        path = str(tmp_path / "out.csv")
        listings_to_csv([_make_listing(date_text="Heute, 14:02")], path)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            row = next(reader)

        assert row["date"] == "Heute, 14:02"

    def test_brand_extracted(self, tmp_path):
        path = str(tmp_path / "out.csv")
        listings_to_csv([_make_listing(title="Hisense 55U71HQ 55 Zoll")], path)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            row = next(reader)

        assert row["brand"] == "Hisense"


# ── Tests: whitespace cleaning ────────────────────────────────────────────────

class TestCleanWhitespace:
    def test_collapses_newlines(self):
        assert _clean_whitespace("10585 Charlottenburg\n\n\n(6 km)") == "10585 Charlottenburg (6 km)"

    def test_collapses_spaces_and_tabs(self):
        assert _clean_whitespace("Berlin   \t  Mitte") == "Berlin Mitte"

    def test_strips_leading_trailing(self):
        assert _clean_whitespace("  hello  ") == "hello"

    def test_empty_string(self):
        assert _clean_whitespace("") == ""

    def test_location_with_messy_whitespace_in_csv(self, tmp_path):
        path = str(tmp_path / "out.csv")
        messy_location = "10585 Charlottenburg\n                    \n\n\n(6 km)"
        listings_to_csv([_make_listing(location=messy_location)], path)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            row = next(reader)

        assert row["location"] == "10585 Charlottenburg (6 km)"


# ── Tests: helper functions ───────────────────────────────────────────────────

class TestNormalizeImageUrls:
    def test_list_uses_pipe(self):
        result = _normalize_image_urls(["https://a.com/1.jpg", "https://b.com/2.jpg"])
        assert result == "https://a.com/1.jpg|https://b.com/2.jpg"

    def test_empty_list(self):
        assert _normalize_image_urls([]) == ""

    def test_single_item(self):
        assert _normalize_image_urls(["https://a.com/1.jpg"]) == "https://a.com/1.jpg"


class TestFindBrand:
    def test_known_brand(self):
        assert _find_brand("Hisense 55U71HQ 55 Zoll") == "Hisense"

    def test_unknown_brand(self):
        assert _find_brand("Fernseher zu verkaufen") == "Unknown"

    def test_empty_text(self):
        assert _find_brand("") == "Unknown"


class TestExtractModel:
    def test_model_after_brand(self):
        result = _extract_model("Hisense 55U71HQ 55 Zoll 4K", brand="Hisense")
        assert "55U71HQ" in result

    def test_no_model_found(self):
        assert _extract_model("", brand=None) == "not sure"
