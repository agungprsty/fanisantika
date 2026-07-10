"""Telegram webhook handler — parse messages and save to Google Sheets."""

import logging
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import Product, TelegramMessage, WebhookResponse
from app.services.sheets import Product, append_product

log = logging.getLogger(__name__)
router = APIRouter()


def _parse_message(text: str) -> dict:
    """Parse a comma-separated message into link, nama, harga.

    Format: "link, nama (opsional), harga (opsional)"
    Example: "https://shopee.co.id/x/123, Serum Wajah, 45000"
    """
    parts = [p.strip() for p in text.split(",")]
    link = parts[0] if len(parts) > 0 else ""
    name = parts[1] if len(parts) > 1 else ""
    price = parts[2] if len(parts) > 2 else ""

    return {"link": link, "name": name, "price": price}


def _validate_link(link: str) -> bool:
    """Check that the link looks valid (starts with http/https)."""
    return bool(re.match(r"^https?://", link))


def _format_reply(product: Product, chat_id: str) -> dict:
    """Format a Telegram reply message."""
    text = f"<b>Produk berhasil disimpan!</b>\n\n"
    text += f"🔗 <b>Link:</b> {product.link}\n"
    if product.name:
        text += f"📦 <b>Nama:</b> {product.name}\n"
    if product.price:
        text += f"💰 <b>Harga:</b> {product.price}\n"
    text += f"\n🏷️ <b>Type:</b> {product.type}\n"
    text += f"\n<i>{product.created_at}</i>"

    return {"chat_id": chat_id, "text": text}


@router.post("/webhook")
async def webhook(request: Request):
    """Handle incoming Telegram webhook messages."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    # Extract message text and chat_id from Telegram payload
    message = TelegramMessage(
        text=body.get("message", {}).get("text", ""),
        chat_id=str(body.get("message", {}).get("chat", {}).get("id", "")),
    )

    if not message.text:
        return JSONResponse(
            status_code=200,
            content={"ok": True},
        )

    log.info(f"Received webhook from chat {message.chat_id}: {message.text}")

    # Parse and validate
    parsed = _parse_message(message.text)
    if not _validate_link(parsed["link"]):
        return JSONResponse(
            status_code=200,
            content=_format_reply(
                Product(link=parsed["link"], name="", price=""), message.chat_id
            ),
        )

    # Save to Google Sheets
    product = append_product(
        credentials_json=settings.GOOGLE_SHEETS_CREDENTIALS,
        spreadsheet_id=settings.SPREADSHEET_ID,
        link=parsed["link"],
        name=parsed["name"],
        price=parsed["price"],
    )

    return JSONResponse(
        status_code=200,
        content=_format_reply(product, message.chat_id),
    )
