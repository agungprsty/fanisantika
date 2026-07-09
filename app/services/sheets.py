"""Google Sheets service for reading and writing products."""

import datetime

import gspread
from google.oauth2.service_account import Credentials


def _get_client(credentials_json: str) -> gspread.Client:
    """Create a gspread client from a JSON string."""
    creds = Credentials.from_service_account_info(
        credentials_json,
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
