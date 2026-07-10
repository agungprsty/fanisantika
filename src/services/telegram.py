"""Telegram webhook handler — parse messages and save to Google Sheets."""

import logging
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.config import settings
from src.models import Product
from src.services.sheets import append_product

log = logging.getLogger(__name__)
router = APIRouter()


def _contains_url(text: str) -> bool:
    """Check if text contains a valid HTTP/HTTPS URL."""
    return bool(re.search(r"https?://[^\s,]+", text))


def _is_command(text: str) -> bool:
    """Check if text starts with a Telegram command (/)."""
    return text.startswith("/")


def _parse_command(text: str) -> tuple:
    """Split text into (command, args)."""
    parts = text.split(maxsplit=1)
    command = parts[0].lower() if parts else ""
    args = parts[1].strip() if len(parts) > 1 else ""
    return command, args


def _parse_message(text: str) -> dict:
    """Parse a comma-separated message into link, nama, harga.

    Args:
        text: Message text (command prefix already stripped if applicable).

    Returns:
        dict with keys: link, name, price.
    """
    parts = [p.strip() for p in text.split(",")]
    link = parts[0] if len(parts) > 0 else ""
    name = parts[1] if len(parts) > 1 else ""
    price = parts[2] if len(parts) > 2 else ""

    return {"link": link, "name": name, "price": price}


def _validate_link(link: str) -> bool:
    """Check that the link looks valid (starts with http/https)."""
    return bool(re.match(r"^https?://", link))


def _build_help_text() -> str:
    """Build HTML help message."""
    return (
        "<b>🤖 Cara Menyimpan Produk</b>\n\n"
        "Gunakan format:\n"
        "<code>link, nama, harga (opsional)</code>\n\n"
        "<b>Contoh:</b>\n"
        "• <code>https://shopee.co.id/..., Serum Wajah, 45000</code>\n"
        "• <code>https://shopee.co.id/..., Serum Wajah</code>\n\n"
        "<b>Perintah:</b>\n"
        "• <code>/add link, nama, harga</code> — Simpan produk\n"
        "• <code>/help</code> — Tampilkan pesan ini\n\n"
        "<i>Nama produk wajib diisi.</i>"
    )


def _build_welcome_text() -> str:
    """Build welcome message for /start."""
    return (
        "<b>👋 Selamat datang di Affiliate Katalog!</b>\n\n"
        "Bot ini membantu kamu menyimpan dan mengelola produk affiliate "
        "ke Google Sheets.\n\n"
        f"{_build_help_text()}"
    )


def _format_reply(product: Product, chat_id: str) -> dict:
    """Format a successful save reply."""
    text = "<b>✅ Produk berhasil disimpan!</b>\n\n"
    text += f"🔗 <b>Link:</b> {product.link}\n"
    text += f"📦 <b>Nama:</b> {product.name}\n"
    if product.price:
        text += f"💰 <b>Harga:</b> {product.price}\n"
    text += f"\n🏷️ <b>Type:</b> {product.type}\n"
    text += f"\n<i>{product.created_at}</i>"

    return {"chat_id": chat_id, "text": text}


def _format_error(message: str, chat_id: str) -> dict:
    """Format an error reply."""
    return {
        "chat_id": chat_id,
        "text": f"<b>❌ Gagal menyimpan produk</b>\n\n{message}\n\n/help — Bantuan",
    }


@router.post("/webhook")
async def webhook(request: Request):
    """Handle incoming Telegram webhook messages."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    chat_id = str(body.get("message", {}).get("chat", {}).get("id", ""))
    text = body.get("message", {}).get("text", "")

    if not text:
        return JSONResponse(status_code=200, content={"ok": True})

    log.info(f"Received webhook from chat {chat_id}: {text}")

    # --- Command handling ---
    if _is_command(text):
        command, args = _parse_command(text)

        if command in ("/start",):
            return JSONResponse(
                status_code=200,
                content={"chat_id": chat_id, "text": _build_welcome_text()},
            )

        if command in ("/help",):
            return JSONResponse(
                status_code=200,
                content={"chat_id": chat_id, "text": _build_help_text()},
            )

        if command in ("/add",):
            if not args:
                return JSONResponse(
                    status_code=200,
                    content=_format_error(
                        "Format: <code>/add link, nama, harga</code>\n\n"
                        "Contoh: <code>/add https://shopee.co.id/..., Serum Wajah, 45000</code>",
                        chat_id,
                    ),
                )

            parsed = _parse_message(args)

            if not parsed["name"]:
                return JSONResponse(
                    status_code=200,
                    content=_format_error(
                        "Nama produk wajib diisi.\n\n"
                        "Format: <code>/add link, nama, harga</code>",
                        chat_id,
                    ),
                )

            if not _validate_link(parsed["link"]):
                return JSONResponse(
                    status_code=200,
                    content=_format_error(
                        "Link tidak valid. Pastikan diawali <code>http://</code> "
                        "atau <code>https://</code>",
                        chat_id,
                    ),
                )

            product = append_product(
                credentials_json=settings.GOOGLE_SHEETS_CREDENTIALS,
                spreadsheet_id=settings.SPREADSHEET_ID,
                link=parsed["link"],
                name=parsed["name"],
                price=parsed["price"],
            )

            return JSONResponse(
                status_code=200,
                content=_format_reply(product, chat_id),
            )

        return JSONResponse(
            status_code=200,
            content=_format_error(
                f"Perintah <code>{command}</code> tidak dikenal.", chat_id
            ),
        )

    # --- Non-command: auto-save if message contains a URL ---
    if not _contains_url(text):
        return JSONResponse(
            status_code=200,
            content={"chat_id": chat_id, "text": _build_help_text()},
        )

    parsed = _parse_message(text)

    if not parsed["name"]:
        return JSONResponse(
            status_code=200,
            content=_format_error(
                "Nama produk wajib diisi.\n\n"
                "Format: <code>link, nama, harga (opsional)</code>\n\n"
                "Contoh: <code>https://shopee.co.id/..., Serum Wajah, 45000</code>",
                chat_id,
            ),
        )

    if not _validate_link(parsed["link"]):
        return JSONResponse(
            status_code=200,
            content=_format_error(
                "Link tidak valid. Pastikan diawali <code>http://</code> "
                "atau <code>https://</code>",
                chat_id,
            ),
        )

    product = append_product(
        credentials_json=settings.GOOGLE_SHEETS_CREDENTIALS,
        spreadsheet_id=settings.SPREADSHEET_ID,
        link=parsed["link"],
        name=parsed["name"],
        price=parsed["price"],
    )

    return JSONResponse(
        status_code=200,
        content=_format_reply(product, chat_id),
    )
