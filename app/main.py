"""FastAPI application with routes for homepage, webhook, and API."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.sheets import read_all_products
from app.services.telegram import router as webhook_router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Affiliate Katalog", version="2.0.0")
app.include_router(webhook_router)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Render the homepage with latest products."""
    try:
        products = read_all_products(
            settings.GOOGLE_SHEETS_CREDENTIALS, settings.SPREADSHEET_ID
        )
    except Exception as e:
        log.error(f"Failed to load products: {e}")
        products = []

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "products": products[:20]},  # show latest 20
    )


@app.get("/api/products")
async def api_products():
    """Return all products as JSON."""
    try:
        products = read_all_products(
            settings.GOOGLE_SHEETS_CREDENTIALS, settings.SPREADSHEET_ID
        )
    except Exception as e:
        log.error(f"Failed to load products for API: {e}")
        products = []

    return [p.model_dump() for p in products]
