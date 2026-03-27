# 📺 Kleinanzeigen TV Deal Finder

A modular Python application that scrapes [kleinanzeigen.de](https://www.kleinanzeigen.de) for second-hand TV listings, filters them by size and recency, scores them using AI (or a built-in heuristic), and returns the **top 3 best deals**.

Includes a mobile-friendly web interface so it can be run online from a smartphone.

## Features

- **Scraper** (`tv_scraper/scraper.py`) – fetches listings via `requests` + `BeautifulSoup` with pagination
- **Filter** (`tv_scraper/filters.py`) – keeps only 55–65″ TVs posted within the last 14 days
- **AI Evaluator** (`tv_scraper/ai_evaluator.py`) – scores listings 0–100 using OpenAI GPT (falls back to heuristic when no API key is set)
- **Web UI** (`tv_scraper/app.py`) – Flask app with a one-button mobile interface
- **CLI** (`tv_scraper/main.py`) – prints JSON + human-readable console output

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2a. Run from the command line
python -m tv_scraper.main

# 2b. Or start the web server (accessible from any device on the network)
python -m tv_scraper.app
# Then open http://<your-ip>:5000 on your smartphone
```

## Configuration

All parameters are in `tv_scraper/config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `POSTAL_CODE` | `13599` | Search centre |
| `RADIUS_KM` | `30` | Search radius in km |
| `PRICE_MIN` / `PRICE_MAX` | `200` / `350` | Price range in € |
| `TV_SIZE_MIN` / `TV_SIZE_MAX` | `55` / `65` | Screen size range in inches |
| `MAX_LISTING_AGE_DAYS` | `14` | Only listings posted within this many days |
| `OPENAI_API_KEY` | *(env var)* | Set to enable AI scoring; otherwise heuristic is used |

## AI Scoring

Set `OPENAI_API_KEY` as an environment variable to enable GPT-powered evaluation:

```bash
export OPENAI_API_KEY="sk-..."
python -m tv_scraper.main
```

Without the key the app uses a built-in heuristic that scores by brand, features, and price.

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Project Structure

```
tv_scraper/
├── __init__.py
├── config.py          # all tuneable parameters
├── scraper.py         # web scraping + data model
├── filters.py         # size & date filters
├── ai_evaluator.py    # OpenAI / heuristic scorer
├── main.py            # CLI entry-point
└── app.py             # Flask web UI
tests/
├── test_config.py
├── test_filters.py
├── test_scraper.py
└── test_ai_evaluator.py
requirements.txt
```
