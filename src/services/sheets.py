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


def _cache_key(credentials_json: str, spreadsheet_id: str) -> str:
    """Generate a deterministic cache key."""
    return f"{hash(credentials_json)}:{spreadsheet_id}"


def _fetch_and_cache(credentials_json: str, spreadsheet_id: str) -> list[Product]:
    """Fetch all products from sheet, sort, store in cache, and return."""
    worksheet = get_spreadsheet(credentials_json, spreadsheet_id).sheet1
    rows = worksheet.get_all_records()

    result = []
    for row in rows:
        row_data = {k.lower(): v for k, v in dict(row).items()}
        if not row_data.get("id"):
            row_data["id"] = 0
        else:
            row_data["id"] = int(row_data["id"])
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


def append_product(
    credentials_json: str,
    spreadsheet_id: str,
    link: str,
    name: str = "",
    price: str = "",
):
    """Append a new product row to the active sheet.

    Column layout (row 1 is header):
      A = id
      B = name
      C = price
      D = link
      E = created_at
      F = type (shopee, tokopedia, etc.)

    Returns a Product object with auto-generated id and created_at.
    """
    worksheet = get_spreadsheet(credentials_json, spreadsheet_id).sheet1

    # Get current max row number for sequential "No" (row 1 is header)
    all_rows = worksheet.get_all_values()
    next_no = int(len(all_rows))
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    product_type = detect_type(link)

    # Write: id, name, price, link, created_at, type
    worksheet.append_row([next_no, name, price, link, created_at, product_type])

    # Invalidate cache agar data baru langsung terbaca
    key = _cache_key(credentials_json, spreadsheet_id)
    _products_cache.pop(key, None)

    return Product(
        id=next_no,
        link=link,
        name=name,
        price=price,
        created_at=created_at,
        type=product_type,
    )
