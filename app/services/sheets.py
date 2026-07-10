"""Google Sheets service for reading and writing products."""

import datetime
import json
import os
import re

import gspread
from google.oauth2.service_account import Credentials

from app.models import Product


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

    return Product(
        id=next_no,
        link=link,
        name=name,
        price=price,
        created_at=created_at,
        type=product_type,
    )


def read_all_products(credentials_json: str, spreadsheet_id: str):
    """Read all products from the active sheet, newest first."""
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

    return sorted(result, key=lambda r: r.id, reverse=True)
