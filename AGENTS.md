# Affiliate Katalog — FastAPI Rewrite

## Project Overview

Affiliate Katalog is a product catalog platform that:
- Receives product data via Telegram bot (`/webhook`)
- Stores products in Google Sheets (via gspread + service account)
- Displays latest products on the homepage (Jinja2 templates)

**Stack**: FastAPI, Python 3, Jinja2, gspread, Vercel Serverless

## File Structure

```
src/
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

User sends: `link, nama (wajib), harga (opsional)`

**Nama produk wajib diisi.** Jika tidak ada nama, bot akan menolak.

Examples:
- `https://shopee.co.id/x/123, Serum Wajah, 45000` → link + nama + harga
- `https://shopee.co.id/x/123, Serum Wajah` → link + nama
- `/add https://shopee.co.id/x/123, Serum Wajah, 45000` → via command

Non-link text (e.g. "Halo", "Jam tangan") → bot balas help.

## Telegram Bot Commands

Register these via BotFather (`/setcommands`):

| Command | Description |
|---------|-------------|
| `/add` | Simpan produk baru (format: /add link, nama, harga) |
| `/help` | Tampilkan panduan penggunaan |
| `/start` | Mulai interaksi dengan bot |

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
uvicorn src.main:app --reload --port 8000
```

## Vercel Deployment

```bash
vercel deploy --prod
```

Ensure `api/index.py` and `vercel.json` are present.
