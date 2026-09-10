# PEB Estimate Assistant

> **Now with accounts, 2FA, a free cloud database option, a free Gemini-powered AI
> assistant, DWG upload, and a Telegram bot.** See `DEPLOYMENT.md` for how to put this
> online for free. Everything below still applies for running it locally first.


A local full-stack tool for **preliminary, non-certified** pre-engineered steel building
estimates (material take-off / weight) and a schematic drawing preview, with a small
learning database of your own past projects, and an optional AI assistant for reading
PIF/PPD/EST files in xlsx, PDF, image, or text format.

> **This tool produces drafts only.** Every estimate and schematic must be reviewed and
> approved by a licensed structural engineer before any real-world use. It does not perform
> wind/seismic load-combination analysis, member design, or connection design, and it does
> not parse DWG files.

## Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, SQLite (local file `peb_estimator.db`)
- **Frontend:** plain HTML/CSS/JavaScript (no build step, no external CDN needed for core
  features — runs fully offline)
- **File parsing:** openpyxl (xlsx), pdfplumber (PDF text)
- **Optional AI:** calls the Anthropic API server-side (your own key, kept in `.env`,
  never exposed to the browser)

## Setup

```bash
cd peb_estimator
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

(Optional) enable the AI Assistant tab:

```bash
cp .env.example .env
# then edit .env and paste your Anthropic API key
```

## Run

```bash
python run.py
```

This starts a local server at **http://127.0.0.1:8000** and opens it in your browser.
A SQLite database file (`peb_estimator.db`) is created automatically in this folder on
first run, seeded with two example historical projects.

To stop: `Ctrl+C` in the terminal.

## Using it

1. **New Estimate** — enter (or AI-extract) building parameters, calculate a draft
   material weight breakdown, export it as CSV.
2. **Historical Projects** — every real, completed project's *actual* total weight you add
   here improves future predictions (nearest-neighbour weighting on width, eave height,
   wind speed, live load, enclosure).
3. **Drawing Preview** — a simple schematic anchor-bolt grid and cross-section, generated
   from your dimensions, clearly marked "not for construction."
4. **AI Assistant** (requires `.env` key) — upload a PIF/PPD/EST file in almost any format;
   the AI drafts parameters + engineering notes, which you can apply into the New Estimate
   form with one click. Always re-check every value.

## Project layout

```
peb_estimator/
  run.py                  entry point
  requirements.txt
  .env.example
  peb_estimator.db        created on first run (SQLite)
  app/
    main.py               FastAPI app + API routes
    database.py            DB engine/session, seed data
    models.py               SQLAlchemy Project model
    schemas.py               Pydantic request/response models
    estimator.py             weight prediction + breakdown logic
    file_parser.py           xlsx/pdf/text extraction, offline regex field-guessing
    ai_extract.py             optional server-side call to Anthropic API
  static/
    index.html
    css/style.css
    js/app.js               UI logic, calls the API
    js/drawing.js            schematic SVG rendering
```

## Optional: Telegram bot

See `extras/README_telegram.md` and `extras/telegram_bot.py` — send a PIF/PPD/EST file
to a Telegram bot and get a draft estimate + notes back in chat, using this same backend.

## Notes on accuracy

Weight prediction is a statistical estimate based on similarity to projects you've added,
not a structural calculation. Treat it the same way you'd treat a rough order-of-magnitude
number from experience — useful for early budgeting, not for fabrication or permitting.
