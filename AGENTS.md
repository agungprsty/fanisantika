# Affiliate Katalog — FastAPI Rewrite

## Project Overview

Affiliate Katalog is a product catalog platform that:
- Receives product data via Telegram bot (`/webhook`)
- Stores products in Google Sheets (via gspread + service account)
- Displays latest products on the homepage (Jinja2 templates)
- Admin dashboard with cookie-based auth for product management
- AI-powered caption generation (Gemini API) for social media posts

**Stack**: FastAPI, Python 3, Jinja2, gspread, Vercel Serverless

## File Structure

```
src/
├── main.py            # FastAPI app entry point + all routes
├── models.py          # Pydantic data models
├── config.py          # Environment settings (pydantic-settings)
├── services/
│   ├── ai.py          # Gemini caption generation
│   ├── admin.py       # Admin auth (cookie-based session + CSRF)
│   ├── telegram.py    # Telegram webhook handler
│   └── sheets.py      # Google Sheets CRUD operations
└── templates/
    ├── index.html     # Homepage (public)
    └── admin/
        ├── dashboard.html  # Admin dashboard (login, table, forms)
        └── threads.html    # Threads content generator page
```

## Key Conventions

- **Naming**: snake_case for variables/functions, PascalCase for classes/models
- **Error handling**: Use FastAPI HTTPException with appropriate status codes (400, 401, 500)
- **Env vars**: Read via `config.py` using pydantic-settings
- **Type hints**: Always use type annotations on function signatures
- **Docstrings**: Google-style docstrings for public functions

## Routes

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/` | Homepage (renders Jinja2 template with latest products) | No |
| POST | `/webhook` | Telegram webhook endpoint — parse & save product messages | No |
| GET | `/api/products` | JSON API returning all products (for JS fetch or testing) | No |
| POST | `/api/captions/generate` | Generate caption via Gemini (for AJAX from dashboard) | No |
| POST | `/api/threads/generate` | Generate Threads "Spill di Reply" content | No |
| POST | `/api/threads/save` | Save Threads content to Google Sheets | Yes |
| GET | `/threads` | Threads content generator page | Yes |
| GET | `/login` | Admin login page | No |
| POST | `/login` | Process login | No |
| POST | `/logout` | Logout | Yes |
| GET | `/dashboard` | Product table with search & pagination | Yes |
| GET | `/product/add` | Add product form | Yes |
| POST | `/product/add` | Save new product + auto-generate caption | Yes |
| GET | `/product/{id}/edit` | Edit caption form | Yes |
| POST | `/product/{id}/edit` | Update caption | Yes |
| POST | `/product/{id}/regenerate` | Regenerate caption via AI | Yes |
| POST | `/product/{id}/delete` | Delete product row from sheet | Yes |
| GET | `/r/{product_id}` | Fast redirect to affiliate link and track click | No |

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
| `/threads <id>` | Generate Threads "Spill di Reply" format |
| `/track <id>` | Cek jumlah klik untuk produk |
| `/stats` | Lihat top 5 produk dengan klik terbanyak |
| `/edit <id>` | Edit nama dan harga produk |
| `/help` | Tampilkan panduan penggunaan |
| `/start` | Mulai interaksi dengan bot |

## Google Sheets Structure

| No | Link | Nama | Harga | Timestamp | Type | caption | threads_content | clicks |
|----|------|------|-------|-----------|------|---------|-----------------|--------|
| 1 | https://... | Serum Wajah | 45000 | 2026-07-09T... | shopee | Caption... | {"angle_type": "...", ...} | 10 |

Column mapping: A=id, B=name, C=price, D=link, E=created_at, F=type, G=caption, H=threads_content, I=clicks

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
