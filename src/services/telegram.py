"""Telegram webhook handler — parse messages and save to Google Sheets."""

import asyncio
import json
import logging
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.config import settings
from src.models import Product
from src.services.sheets import (
    append_product,
    read_all_products,
    update_product,
)

log = logging.getLogger(__name__)
router = APIRouter()


# ── In-memory state: which chat is currently editing which product ────────────

_editing_state: dict[str, dict] = {}  # chat_id -> {"product_id": int, "link": str, "type": str}


# ── Helpers ──────────────────────────────────────────────────────────────────

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


# ── AI extraction ───────────────────────────────────────────────────────────

_EXTRACT_SYSTEM_PROMPT = (
    "Kamu adalah asisten yang mengekstrak informasi produk dari teks bebas. "
    "Tulis nama produk dengan benar, perbaiki typo seperti:\n"
    "- JamDinding → Jam Dinding\n"
    "- Hme → Home\n"
    "- LaptopBuka → Laptop Buka\n"
    "- SepatuSneakers → Sepatu Sneakers\n"
    "Hilangkan kata filler yang tidak perlu (HOME, Hiasan Dinding, Kamar tidur).\n"
    "Batasi nama maksimal 8 kata.\n"
    "Tulis harga dalam format k (contoh: 10000 → 10k, 35000 → 35k).\n"
    "Kembalikan hanya JSON valid, tanpa teks lain."
)


async def _extract_product_info_from_ai(text: str) -> dict | None:
    """Extract link, name, price, type from a free-form message using AI.

    Args:
        text: Free-form product message (e.g. copy-pasted from Shopee).

    Returns:
        dict with keys: link, name, price, type — or None if extraction fails.
    """
    if not settings.OPENROUTER_API_KEY:
        return None

    prompt = (
        f"Extract link, name, price, dan type dari pesan ini.\n\n"
        f"Pesan:\n{text}\n\n"
        "Rules for name:\n"
        "- Maximum 8 words, aim for ~6\n"
        "- Fix common typos (JamDinding → Jam Dinding, Hme → Home)\n"
        "- Remove redundant filler (HOME, Hiasan Dinding, Kamar tidur) if they don't add meaning\n"
        "- Keep the most descriptive part of the name\n\n"
        "Rules for price:\n"
        "- Convert to k format (10000 → 10k, 35000 → 35k)\n"
        "- If no price found, return empty string\n\n"
        "Rules for type:\n"
        "- Infer from URL (shopee, tokopedia, lazada, bukalapak, tiktok, other)\n\n"
        "Return ONLY valid JSON: {\"link\": \"...\", \"name\": \"...\", \"price\": \"...\", \"type\": \"...\"}"
    )

    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
        max_retries=0,
    )

    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model="openrouter/free",
                messages=[
                    {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                extra_headers={
                    "HTTP-Referer": "https://github.com/agungprsty/fanisantika",
                    "X-Title": "Affiliate Product Extractor",
                },
            )

            content = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
            data = json.loads(content)

            result = {
                "link": str(data.get("link", "")).strip(),
                "name": str(data.get("name", "")).strip(),
                "price": str(data.get("price", "")).strip().replace(".", "").replace(",", ""),
                "type": str(data.get("type", "other")).strip(),
            }

            if result["link"] and _validate_link(result["link"]):
                log.info(f"AI extracted: name='{result['name']}', price={result['price']}, type={result['type']}")
                return result

            log.warning("AI extraction returned empty link")
            return None

        except (json.JSONDecodeError, KeyError) as e:
            log.error(f"AI extract JSON error: {e}")
            return None
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "502" in error_msg or "503" in error_msg:
                if attempt < 2:
                    wait_time = (attempt + 1) * 3
                    log.warning(f"AI extract server busy. Waiting {wait_time}s (attempt {attempt+1}/3)...")
                    await asyncio.sleep(wait_time)
                    continue
            log.error(f"AI extraction failed: {e}")
            return None

    return None


# ── Build messages ──────────────────────────────────────────────────────────

def _build_help_text() -> str:
    """Build HTML help message."""
    return (
        "<b>🤖 Cara Menyimpan Produk</b>\n\n"
        "Format koma:\n"
        "<code>link, nama, harga (opsional)</code>\n\n"
        "Atau copy-paste langsung dari Shopee:\n"
        "<code>Temukan JamDinding Ukir HOME Sweet Hme Bunga Matahari Hiasan Dinding Ruang Tamu Kamar tidur seharga Rp34.002. Dapatkan sekarang juga di Shopee! https://s.shopee.co.id/2BDNa9ihtR?share_channel_code=2</code>\n\n"
        "<b>Perintah:</b>\n"
        "• <code>/add link, nama, harga</code> — Simpan produk (format koma)\n"
        "• <code>/edit 3</code> — Edit produk #3 (kirim: <code>nama baru, harga baru</code>)\n"
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


def _format_price(price: str) -> str:
    """Convert numeric price to k format (10000 → 10k, 35000 → 35k)."""
    if not price:
        return ""
    try:
        num = float(str(price).replace(".", "").replace(",", "").strip())
        if num >= 1000:
            k_value = int(num / 1000)
            remainder = num % 1000
            if remainder > 0:
                return f"{k_value}k{remainder // 100}"
            return f"{k_value}k"
        return str(int(num))
    except (ValueError, TypeError):
        return price


def _format_reply(product: Product, chat_id: str) -> dict:
    """Format a successful save reply."""
    text = "<b>✅ Produk berhasil disimpan!</b>\n\n"
    text += f"🔗 <b>Link:</b> {product.link}\n"
    text += f"📦 <b>Nama:</b> {product.name}\n"
    if product.price:
        text += f"💰 <b>Harga:</b> {_format_price(product.price)}\n"
    text += f"\n🏷️ <b>Type:</b> {product.type}\n"
    text += f"\n<i>{product.created_at}</i>"

    return {"method": "sendMessage", "chat_id": chat_id, "text": text, "parse_mode": "HTML"}


def _format_error(message: str, chat_id: str) -> dict:
    """Format an error reply."""
    return {
        "method": "sendMessage",
        "chat_id": chat_id,
        "text": f"<b>❌ Gagal menyimpan produk</b>\n\n{message}\n\n/help — Bantuan",
        "parse_mode": "HTML",
    }


# ── Routes ───────────────────────────────────────────────────────────────────

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
                content={
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": _build_welcome_text(),
                    "parse_mode": "HTML",
                },
            )

        if command in ("/help",):
            return JSONResponse(
                status_code=200,
                content={
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": _build_help_text(),
                    "parse_mode": "HTML",
                },
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

            if settings.CAPTION_ENABLED:
                from src.services.ai import generate_caption

                try:
                    caption = await generate_caption(
                        name=product.name, price=product.price,
                        link=product.link, platform=product.type,
                    )
                    if caption:
                        update_product(
                            settings.GOOGLE_SHEETS_CREDENTIALS,
                            settings.SPREADSHEET_ID,
                            product.id, caption=caption,
                        )
                        product.caption = caption
                except Exception:
                    log.exception("Caption generation failed after /add")

            return JSONResponse(
                status_code=200,
                content=_format_reply(product, chat_id),
            )

        if command in ("/edit",):
            if not args:
                return JSONResponse(
                    status_code=200,
                    content=_format_error(
                        "Format: <code>/edit &lt;id&gt;</code>\n\n"
                        "Contoh: <code>/edit 3</code>",
                        chat_id,
                    ),
                )

            try:
                product_id = int(args)
            except ValueError:
                return JSONResponse(
                    status_code=200,
                    content=_format_error(
                        f"<code>{args}</code> bukan ID produk yang valid.\n\n"
                        "Format: <code>/edit &lt;id&gt;</code>",
                        chat_id,
                    ),
                )

            # Find product by ID
            products = read_all_products(
                credentials_json=settings.GOOGLE_SHEETS_CREDENTIALS,
                spreadsheet_id=settings.SPREADSHEET_ID,
                limit=9999,
                offset=0,
            )
            product = next((p for p in products if p.id == product_id), None)

            if not product:
                return JSONResponse(
                    status_code=200,
                    content=_format_error(
                        f"Produk dengan ID <b>{product_id}</b> tidak ditemukan.\n\n"
                        f"Total produk: {len(products)}",
                        chat_id,
                    ),
                )

            # Set editing state
            _editing_state[chat_id] = {
                "product_id": product.id,
                "link": product.link,
                "type": product.type,
            }

            return JSONResponse(
                status_code=200,
                content={
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": (
                        f"<b>Edit produk #{product.id}</b>\n\n"
                        f"📦 <b>Nama:</b> {product.name}\n"
                        f"💰 <b>Harga:</b> {_format_price(product.price)}\n"
                        f"🔗 <b>Link:</b> {product.link}\n\n"
                        "Kirim nama baru dan harga baru (opsional):\n"
                        "• <code>Nama Baru</code> — hanya ubah nama\n"
                        "• <code>Nama Baru, 50k</code> — ubah nama & harga\n"
                        "• <code>, 60k</code> — hanya ubah harga\n"
                    ),
                    "parse_mode": "HTML",
                },
            )

        return JSONResponse(
            status_code=200,
            content=_format_error(
                f"Perintah <code>{command}</code> tidak dikenal.\n\n"
                "<code>/add link, nama, harga</code> atau <code>/edit &lt;id&gt;</code>",
                chat_id,
            ),
        )

    # --- Reply to edit command (editing mode) ---
    if chat_id in _editing_state:
        state = _editing_state[chat_id]
        parts = [p.strip() for p in text.split(",")]

        new_name = parts[0] if len(parts) > 0 else ""
        new_price = parts[1] if len(parts) > 1 else ""

        # Clear editing state
        _editing_state.pop(chat_id, None)

        if not new_name and not new_price:
            return JSONResponse(
                status_code=200,
                content=_format_error("Nama atau harga harus diisi.", chat_id),
            )

        try:
            update_product(
                credentials_json=settings.GOOGLE_SHEETS_CREDENTIALS,
                spreadsheet_id=settings.SPREADSHEET_ID,
                product_id=state["product_id"],
                name=new_name if new_name else None,
                price=new_price if new_price else None,
            )

            return JSONResponse(
                status_code=200,
                content={
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": (
                        f"<b>✅ Produk #{state['product_id']} berhasil diupdate!</b>\n\n"
                        f"📦 <b>Nama:</b> {new_name or state.get('name', '')}\n"
                        f"💰 <b>Harga:</b> {_format_price(new_price) if new_price else (state.get('price', ''))}"
                    ),
                    "parse_mode": "HTML",
                },
            )
        except Exception as e:
            log.error(f"Failed to update product {state['product_id']}: {e}")
            return JSONResponse(
                status_code=200,
                content=_format_error(
                    f"Gagal update produk #{state['product_id']}: {e}",
                    chat_id,
                ),
            )

    # --- Non-command: auto-save if message contains a URL ---
    if not _contains_url(text):
        return JSONResponse(
            status_code=200,
            content={
                "method": "sendMessage",
                "chat_id": chat_id,
                "text": _build_help_text(),
                "parse_mode": "HTML",
            },
        )

    # Choose parsing strategy based on message length
    parsed: dict = {}
    if len(text) >= 70:
        # Use AI extraction for longer messages (copy-pasted from Shopee)
        ai_result = await _extract_product_info_from_ai(text)
        if ai_result and ai_result["name"]:
            parsed = ai_result
        else:
            log.info("AI extraction returned empty, falling back to regex")
            parsed = _parse_message(text)
    else:
        # Fast regex for short messages
        parsed = _parse_message(text)

    if not parsed.get("name"):
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
        price=parsed.get("price", ""),
    )

    if settings.CAPTION_ENABLED:
        from src.services.ai import generate_caption

        try:
            caption = await generate_caption(
                name=product.name, price=product.price,
                link=product.link, platform=product.type,
            )
            if caption:
                update_product(
                    settings.GOOGLE_SHEETS_CREDENTIALS,
                    settings.SPREADSHEET_ID,
                    product.id, caption=caption,
                )
                product.caption = caption
        except Exception:
            log.exception("Caption generation failed after auto-save")

    return JSONResponse(
        status_code=200,
        content=_format_reply(product, chat_id),
    )
