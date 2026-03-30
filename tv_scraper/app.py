"""
Minimal Flask web interface so the scraper can be used from a smartphone.

Run with:
    python -m tv_scraper.app          # development
    gunicorn tv_scraper.app:app       # production
"""

import logging
import os

from flask import Flask, jsonify, render_template_string, send_file

from tv_scraper.cache import cache_timestamp, is_cache_fresh, load_cache, save_cache
from tv_scraper.config import (
    CSV_OUTPUT,
    POSTAL_CODE,
    PRICE_MAX,
    PRICE_MIN,
    TV_SIZE_MAX,
    TV_SIZE_MIN,
)
from tv_scraper.export_csv import listings_to_csv
from tv_scraper.filters import filter_listings
from tv_scraper.scraper import scrape_listings

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# ── HTML template (single-file, mobile-friendly) ─────────────────────────────
_HTML = """\
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TV Deal Finder</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
           sans-serif; background: #f5f5f5; color: #222; padding: 16px; }
    h1 { font-size: 1.4rem; margin-bottom: 12px; text-align: center; }
    .card { background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.1);
            padding: 16px; margin-bottom: 16px; }
    .card h2 { font-size: 1rem; margin-bottom: 6px; }
    .meta { font-size: .85rem; color: #666; margin-bottom: 4px; }
    a { color: #1976d2; text-decoration: none; }
    .btn { display: block; text-align: center; margin: 20px auto;
           padding: 12px 24px; background: #1976d2; color: #fff;
           border: none; border-radius: 8px; font-size: 1rem;
           cursor: pointer; max-width: 300px; }
    .btn:disabled { background: #aaa; }
    .btn-csv { background: #388e3c; }
    .spinner { display: none; text-align: center; margin: 20px 0; }
    .error { color: #d32f2f; text-align: center; margin: 12px 0; }
  </style>
</head>
<body>
  <h1>📺 TV Deal Finder</h1>
  <p style="text-align:center; font-size:.9rem; margin-bottom:16px;">
    Searches kleinanzeigen.de for {{ tv_size_min }}–{{ tv_size_max }}″ TV deals near {{ postal_code }}
    (price: {{ price_min }}–{{ price_max }} €).
  </p>
  <button class="btn" id="searchBtn" onclick="doSearch()">🔍 Search Deals</button>
  <div class="spinner" id="spinner">⏳ Searching… this may take a minute.</div>
  <div id="error" class="error"></div>
  <div id="results"></div>

  <script>
    async function doSearch() {
      const btn = document.getElementById('searchBtn');
      const spinner = document.getElementById('spinner');
      const errDiv = document.getElementById('error');
      const resultsDiv = document.getElementById('results');
      btn.disabled = true;
      spinner.style.display = 'block';
      errDiv.textContent = '';
      resultsDiv.innerHTML = '';
      try {
        const res = await fetch('/api/search');
        const data = await res.json();
        if (data.error) { errDiv.textContent = data.error; return; }
        if (!data.results || data.results.length === 0) {
          resultsDiv.innerHTML = '<p style="text-align:center">No matching listings found.</p>';
          return;
        }
        data.results.forEach((r, i) => {
          resultsDiv.innerHTML += `
            <div class="card">
              <h2>#${i+1} ${esc(r.title)}</h2>
              <p class="meta">💰 ${esc(r.price)}</p>
              <p class="meta">📍 ${esc(r.location)} &nbsp; 📅 ${esc(r.date)}</p>
              ${r.description ? `<p style="margin-top:6px;font-size:.9rem">${esc(r.description)}</p>` : ''}
              <p style="margin-top:6px"><a href="${esc(r.url)}" target="_blank">Open listing ↗</a></p>
            </div>`;
        });
        resultsDiv.innerHTML += `
          <a class="btn btn-csv" href="/api/download_csv">⬇ Download CSV</a>`;
        if (data.cached) {
          resultsDiv.innerHTML += `<p style="text-align:center;font-size:.8rem;color:#888;margin-top:8px">
            ⚡ Results from cache (scraped at ${esc(data.cached_at)}).
            Data is re-fetched automatically after 1 hour.</p>`;
        }
      } catch (e) { errDiv.textContent = 'Request failed: ' + e; }
      finally { btn.disabled = false; spinner.style.display = 'none'; }
    }
    function esc(s) {
      const d = document.createElement('div');
      d.textContent = s || '';
      return d.innerHTML;
    }
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(
        _HTML,
        tv_size_min=TV_SIZE_MIN,
        tv_size_max=TV_SIZE_MAX,
        postal_code=POSTAL_CODE,
        price_min=PRICE_MIN,
        price_max=PRICE_MAX,
    )


@app.route("/api/search")
def api_search():
    try:
        cached = is_cache_fresh()
        if cached:
            raw = load_cache()
        else:
            raw = scrape_listings()
            save_cache(raw)
        filtered = filter_listings(raw)
        if not filtered:
            return jsonify({"results": [], "total_raw": len(raw), "cached": cached, "cached_at": cache_timestamp()})
        listings_to_csv(filtered, CSV_OUTPUT)
        results = [
            {
                "title": l.title,
                "price": l.price,
                "description": l.description,
                "location": l.location,
                "date": l.date_text,
                "url": l.url,
            }
            for l in filtered
        ]
        return jsonify({
            "results": results,
            "total_raw": len(raw),
            "total_filtered": len(filtered),
            "cached": cached,
            "cached_at": cache_timestamp(),
        })
    except Exception as exc:
        logging.exception("Search failed")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/download_csv")
def download_csv():
    if not os.path.exists(CSV_OUTPUT):
        return jsonify({"error": "No CSV available yet. Run a search first."}), 404
    return send_file(CSV_OUTPUT, as_attachment=True, download_name="tv_listings.csv", mimetype="text/csv")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
