"""Google Sheets service for reading and writing products."""

import datetime
import json
import os

import gspread
from google.oauth2.service_account import Credentials


def _get_client(credentials_json: str) -> gspread.Client:
    """Create a gspread client from a JSON string, dict, or file path.

    Supports three formats for GOOGLE_SHEETS_CREDENTIALS:
      1. A raw JSON object (string or dict)
      2. A path to a .json file (e.g. "service_account.json")
    """
    if isinstance(credentials_json, str):
        # Check if it looks like a file path (ends with .json or exists as file)
        if credentials_json.endswith(".json") and os.path.isfile(credentials_json):
            with open(credentials_json, "r") as f:
                credentials_dict = json.load(f)
        elif credentials_json.startswith("{"):
            # Try parsing as JSON string
            normalized = credentials_json.replace("\\n", "\n")
            credentials_dict = json.loads(normalized)
        else:
            credentials_dict = credentials_json
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
    nama: str = "",
    harga: str = "",
):
    """Append a new product row to the active sheet.

    Returns the created Product dict with auto-generated no and timestamp.
    """
    worksheet = get_spreadsheet(credentials_json, spreadsheet_id).sheet1

    # Get current max row number for sequential "No"
    all_rows = worksheet.get_all_values()
    next_no = len(all_rows) + 1 if all_rows else 1
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    worksheet.append_row([str(next_no), link, nama, harga, timestamp])

    return {
        "no": str(next_no),
        "link": link,
        "nama": nama,
        "harga": harga,
        "timestamp": timestamp,
    }


def read_all_products(credentials_json: str, spreadsheet_id: str):
    """Read all products from the active sheet, newest first."""
    worksheet = get_spreadsheet(credentials_json, spreadsheet_id).sheet1
    rows = worksheet.get_all_records()

    # Sort by no descending (newest first)
    products = sorted(rows, key=lambda r: int(r.get("No", 0)), reverse=True)
    return [Product(**row) for row in products]
