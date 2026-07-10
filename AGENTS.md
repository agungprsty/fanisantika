# Affiliate Katalog — FastAPI Rewrite

## Project Overview

Affiliate Katalog is a product catalog platform that:
- Receives product data via Telegram bot (`/webhook`)
- Stores products in Google Sheets (via gspread + service account)
- Displays latest products on the homepage (Jinja2 templates)

**Stack**: FastAPI, Python 3, Jinja2, gspread, Vercel Serverless

## File Structure

```
app/
├── main.py            # FastAPI app entry point + routes
├── models.py          # Pydantic data models
├── config.py          # Environment settings (pydantic-settings)
├── services/
│   ├── telegram.py    # Telegram webhook handler
│   └── sheets.py      # Google Sheets CRUD operations
└── templates/         # Jinja2 HTML templates
```

## Key Conventions

- **Naming**: snake_case for variables/functions, PascalCase for classes/models
- **Error handling**: Use FastAPI HTTPException with appropriate status codes (400, 401, 500)
- **Env vars**: Read via `config.py` using pydantic-settings
- **Type hints**: Always use type annotations on function signatures
- **Docstrings**: Google-style docstrings for public functions

## Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Homepage (renders Jinja2 template with latest products) |
| POST | `/webhook` | Telegram webhook endpoint — parse & save product messages |
| GET | `/api/products` | JSON API returning all products (for JS fetch or testing) |

## Telegram Message Format

User sends: `link, nama (opsional), harga (opsional)`

Examples:
- `https://shopee.co.id/x/123` → link only
- `https://shopee.co.id/x/123, Serum Wajah` → link + nama
- `https://shopee.co.id/x/123, Serum Wajah, 45000` → full data

## Google Sheets Structure

| No | Link | Nama | Harga | Timestamp |
|----|------|------|-------|-----------|
| 1 | https://... | Serum Wajah | 45000 | 2026-07-09T... |

## Environment Variables

See `.env.example` for all required vars. Copy to `.env` before running locally.

## Running Locally

```bash
pip install -r requirements.txt
cp .env.example .env  # then fill in your values
uvicorn app.main:app --reload --port 8000
```

## Vercel Deployment

```bash
vercel deploy --prod
```

Ensure `api/index.py` and `vercel.json` are present.
