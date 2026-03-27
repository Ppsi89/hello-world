"""
Minimal Flask web interface so the scraper can be used from a smartphone.

Run with:
    python -m tv_scraper.app          # development
    gunicorn tv_scraper.app:app       # production
"""

import json
import logging
import os

from flask import Flask, jsonify, render_template_string

from tv_scraper.ai_evaluator import evaluate, top_results
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
    .score { display: inline-block; background: #4caf50; color: #fff;
             border-radius: 6px; padding: 2px 8px; font-weight: bold; }
    .features { font-size: .85rem; color: #1976d2; }
    a { color: #1976d2; text-decoration: none; }
    .btn { display: block; text-align: center; margin: 20px auto;
           padding: 12px 24px; background: #1976d2; color: #fff;
           border: none; border-radius: 8px; font-size: 1rem;
           cursor: pointer; max-width: 300px; }
    .btn:disabled { background: #aaa; }
    .spinner { display: none; text-align: center; margin: 20px 0; }
    .error { color: #d32f2f; text-align: center; margin: 12px 0; }
  </style>
</head>
<body>
  <h1>📺 TV Deal Finder</h1>
  <p style="text-align:center; font-size:.9rem; margin-bottom:16px;">
    Searches kleinanzeigen.de for the best 55–65″ TV deals near 13599 Berlin.
  </p>
  <button class="btn" id="searchBtn" onclick="doSearch()">🔍 Search Deals</button>
  <div class="spinner" id="spinner">⏳ Searching &amp; analysing… this may take a minute.</div>
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
              <p class="meta">💰 ${esc(r.price)} &nbsp; <span class="score">${r.score}/100</span></p>
              <p class="meta">📍 ${esc(r.location)} &nbsp; 📅 ${esc(r.date)}</p>
              <p class="features">${(r.features||[]).join(', ') || '–'}</p>
              <p style="margin-top:6px">${esc(r.summary)}</p>
              <p style="margin-top:6px"><a href="${esc(r.url)}" target="_blank">Open listing ↗</a></p>
            </div>`;
        });
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
    return render_template_string(_HTML)


@app.route("/api/search")
def api_search():
    try:
        raw = scrape_listings()
        filtered = filter_listings(raw)
        if not filtered:
            return jsonify({"results": [], "total_raw": len(raw)})
        scored = evaluate(filtered)
        best = top_results(scored)
        results = [
            {
                "title": s.listing.title,
                "price": s.listing.price,
                "score": round(s.score, 1),
                "summary": s.summary,
                "brand": s.brand,
                "year": s.year,
                "features": s.features,
                "location": s.listing.location,
                "date": s.listing.date_text,
                "url": s.listing.url,
            }
            for s in best
        ]
        return jsonify({"results": results, "total_raw": len(raw), "total_filtered": len(filtered)})
    except Exception as exc:
        logging.exception("Search failed")
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug)
