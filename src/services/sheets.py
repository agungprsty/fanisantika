"""Google Sheets service for reading and writing products."""

import datetime
import json
import logging

import gspread
from cachetools import TTLCache
from google.oauth2.service_account import Credentials

from src.models import Product

log = logging.getLogger(__name__)

# Module-level cache: key -> list[Product], TTL 60 detik
# Cache di-share antar request dalam proses yang sama
_products_cache: TTLCache = TTLCache(maxsize=1, ttl=60)

# Track max ID in memory to avoid re-scanning all rows on every append
_max_id: int = 0


def _init_max_id(credentials_json: str, spreadsheet_id: str) -> int:
    """Compute and cache the current max ID from Google Sheets."""
    global _max_id
    worksheet = get_spreadsheet(credentials_json, spreadsheet_id).sheet1
    all_rows = worksheet.get_all_values()
    existing_ids = [int(r[0]) for r in all_rows[1:] if r and r[0].isdigit()]
    _max_id = max(existing_ids, default=0)
    return _max_id


def _reset_max_id_if_needed(credentials_json: str, spreadsheet_id: str) -> None:
    """Reset _max_id to 0 when cache is invalidated so next append recomputes."""
    global _max_id
    _max_id = 0


def detect_type(link: str) -> str:
    """Detect the platform type from a product link."""
    link_lower = link.lower()
    if "shopee" in link_lower or "s.id" in link_lower:
        return "shopee"
    elif "tokopedia" in link_lower:
        return "tokopedia"
    elif "lazada" in link_lower:
        return "lazada"
    elif "bukalapak" in link_lower:
        return "bukalapak"
    elif "tiktok" in link_lower or "ttshop" in link_lower:
        return "tiktok"
    else:
        return "other"


def _get_client(credentials_json: str) -> gspread.Client:
    """Create a gspread client from a JSON string or dict."""
    if isinstance(credentials_json, str):
        credentials_dict = json.loads(credentials_json)
    else:
        credentials_dict = credentials_json

    creds = Credentials.from_service_account_info(
        credentials_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds)


def get_spreadsheet(credentials_json: str, spreadsheet_id: str):
    """Open a specific spreadsheet by ID."""
    client = _get_client(credentials_json)
    return client.open_by_key(spreadsheet_id)


def _ensure_caption_column(worksheet):
    """Add caption column (G) to header if it doesn't exist."""
    header_lower = [h.lower() for h in worksheet.row_values(1)]
    if "caption" in header_lower:
        return
    col_idx = len(header_lower) + 1
    worksheet.update_cell(1, col_idx, "caption")
    log.info("Added 'caption' column to sheet header (col %d)", col_idx)


def _ensure_threads_column(worksheet):
    """Add threads_content column (H) to header if it doesn't exist."""
    header_lower = [h.lower() for h in worksheet.row_values(1)]
    if "threads_content" in header_lower:
        return
    col_idx = len(header_lower) + 1
    worksheet.update_cell(1, col_idx, "threads_content")
    log.info("Added 'threads_content' column to sheet header (col %d)", col_idx)


def _cache_key(credentials_json: str, spreadsheet_id: str) -> str:
    """Generate a deterministic cache key."""
    return f"{hash(credentials_json)}:{spreadsheet_id}"


def _fetch_and_cache(credentials_json: str, spreadsheet_id: str) -> list[Product]:
    """Fetch all products from sheet, sort, store in cache, and return."""
    worksheet = get_spreadsheet(credentials_json, spreadsheet_id).sheet1
    _ensure_caption_column(worksheet)
    _ensure_threads_column(worksheet)
    rows = worksheet.get_all_records()

    result = []
    for row in rows:
        row_data = {k.lower(): v for k, v in dict(row).items()}
        if not row_data.get("id"):
            row_data["id"] = 0
        else:
            row_data["id"] = int(row_data["id"])
        row_data["price"] = str(row_data.get("price", ""))
        if not row_data.get("type"):
            row_data["type"] = detect_type(row_data.get("link", ""))
        result.append(Product(**row_data))

    result.sort(key=lambda r: r.id)

    key = _cache_key(credentials_json, spreadsheet_id)
    _products_cache[key] = result
    return result


def read_all_products(
    credentials_json: str,
    spreadsheet_id: str,
    limit: int = 20,
    offset: int = 0,
    q: str = "",
):
    """Read products from the active sheet with caching, search & pagination.

    Args:
        credentials_json: Google service account credentials JSON string.
        spreadsheet_id: ID of the Google Spreadsheet.
        limit: Maximum number of products to return (default 20).
        offset: Number of products to skip (default 0).
        q: Optional search query — case-insensitive substring match
           on name, id, link, or type.

    Returns:
        List of Product objects.
    """
    key = _cache_key(credentials_json, spreadsheet_id)

    if key not in _products_cache:
        _fetch_and_cache(credentials_json, spreadsheet_id)

    products = _products_cache[key]

    if q:
        q_lower = q.lower()
        products = [
            p
            for p in products
            if q_lower in p.name.lower()
            or q_lower in str(p.link).lower()
            or q in str(p.id)
            or q_lower in p.type.lower()
        ]

    return products[offset : offset + limit]


def count_all_products(
    credentials_json: str,
    spreadsheet_id: str,
    q: str = "",
) -> int:
    """Return total number of products (with optional search filter)."""
    key = _cache_key(credentials_json, spreadsheet_id)

    if key not in _products_cache:
        _fetch_and_cache(credentials_json, spreadsheet_id)

    products = _products_cache[key]

    if q:
        q_lower = q.lower()
        products = [
            p
            for p in products
            if q_lower in p.name.lower()
            or q_lower in str(p.link).lower()
            or q in str(p.id)
            or q_lower in p.type.lower()
        ]

    return len(products)


def append_product(
    credentials_json: str,
    spreadsheet_id: str,
    link: str,
    name: str = "",
    price: str = "",
    caption: str = "",
):
    """Append a new product row to the active sheet.

    Column layout (row 1 is header):
      A = id
      B = name
      C = price
      D = link
      E = created_at
      F = type (shopee, tokopedia, etc.)
      G = caption

    Args:
        caption: Initial AI caption (empty string if not generated).

    Returns a Product object with auto-generated id and created_at.
    """
    worksheet = get_spreadsheet(credentials_json, spreadsheet_id).sheet1

    # Ensure caption and threads columns exist
    _ensure_caption_column(worksheet)
    _ensure_threads_column(worksheet)

    # Use cached max_id; recompute only if reset by a previous operation
    if _max_id == 0:
        _init_max_id(credentials_json, spreadsheet_id)
    next_no = _max_id + 1
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    product_type = detect_type(link)

    # Write: id, name, price, link, created_at, type, caption
    worksheet.append_row([next_no, name, price, link, created_at, product_type, caption])

    # Invalidate cache agar data baru langsung terbaca
    key = _cache_key(credentials_json, spreadsheet_id)
    _products_cache.pop(key, None)
    _reset_max_id_if_needed(credentials_json, spreadsheet_id)

    return Product(
        id=next_no,
        link=link,
        name=name,
        price=price,
        created_at=created_at,
        type=product_type,
        caption=caption,
    )


def update_product(
    credentials_json: str,
    spreadsheet_id: str,
    product_id: int,
    name: str | None = None,
    price: str | None = None,
    caption: str | None = None,
) -> bool:
    """Update name (B), price (C), and/or caption (G) for a given product.

    Only columns with non-None values are updated.
    Returns True if found and updated, False otherwise.
    """
    worksheet = get_spreadsheet(credentials_json, spreadsheet_id).sheet1
    all_rows = worksheet.get_all_values()

    for i, row in enumerate(all_rows):
        if i == 0:
            continue
        if row and row[0].isdigit() and int(row[0]) == product_id:
            row_idx = i + 1  # 1-based
            if name is not None:
                worksheet.update_cell(row_idx, 2, name)  # col B
            if price is not None:
                worksheet.update_cell(row_idx, 3, price)  # col C
            if caption is not None:
                worksheet.update_cell(row_idx, 7, caption)  # col G
            log.info("Updated product id=%d", product_id)

            key = _cache_key(credentials_json, spreadsheet_id)
            _products_cache.pop(key, None)
            _reset_max_id_if_needed(credentials_json, spreadsheet_id)
            return True

    log.warning("Product id=%d not found for update", product_id)
    return False


def update_product_caption(
    credentials_json: str,
    spreadsheet_id: str,
    product_id: int,
    caption: str,
) -> bool:
    """Update only the caption for a given product.

    Returns True if found and updated, False otherwise.
    """
    return update_product(
        credentials_json=credentials_json,
        spreadsheet_id=spreadsheet_id,
        product_id=product_id,
        caption=caption,
    )


def update_product_threads(
    credentials_json: str,
    spreadsheet_id: str,
    product_id: int,
    threads_content: str,
) -> bool:
    """Update only the threads_content for a given product.

    Returns True if found and updated, False otherwise.
    """
    worksheet = get_spreadsheet(credentials_json, spreadsheet_id).sheet1
    _ensure_threads_column(worksheet)
    all_rows = worksheet.get_all_values()

    # Find threads column index from header
    header = [h.lower() for h in all_rows[0]] if all_rows else []
    threads_col = None
    for idx, h in enumerate(header):
        if h == "threads_content":
            threads_col = idx + 1  # 1-based
            break

    if not threads_col:
        threads_col = len(header) + 1
        worksheet.update_cell(1, threads_col, "threads_content")

    for i, row in enumerate(all_rows):
        if i == 0:
            continue
        if row and row[0].isdigit() and int(row[0]) == product_id:
            row_idx = i + 1
            worksheet.update_cell(row_idx, threads_col, threads_content)
            log.info("Updated threads_content for product id=%d", product_id)

            key = _cache_key(credentials_json, spreadsheet_id)
            _products_cache.pop(key, None)
            _reset_max_id_if_needed(credentials_json, spreadsheet_id)
            return True

    log.warning("Product id=%d not found for threads update", product_id)
    return False


def delete_product_row(
    credentials_json: str,
    spreadsheet_id: str,
    product_id: int,
) -> bool:
    """Delete the entire row for a given product.

    Returns True if found and deleted, False otherwise.
    """
    worksheet = get_spreadsheet(credentials_json, spreadsheet_id).sheet1
    all_rows = worksheet.get_all_values()

    for i, row in enumerate(all_rows):
        if i == 0:
            continue
        if row and row[0].isdigit() and int(row[0]) == product_id:
            worksheet.delete_rows(i + 1)  # 1-based row index
            log.info("Deleted product id=%d (row %d)", product_id, i + 1)

            # Invalidate cache
            key = _cache_key(credentials_json, spreadsheet_id)
            _products_cache.pop(key, None)
            _reset_max_id_if_needed(credentials_json, spreadsheet_id)
            return True

    log.warning("Product id=%d not found for deletion", product_id)
    return False
