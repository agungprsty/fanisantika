---
name: google-sheets
description: Interact with Google Sheets API using gspread + service account — read, append, and manage spreadsheet data
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: data-storage
---

## What I do
- Initialize gspread client with service account credentials (JSON string or file)
- Open a specific spreadsheet by ID
- Read all rows from the active sheet
- Append new rows with automatic column ordering
- Handle authentication via `GOOGLE_SHEETS_CREDENTIALS` env var

## When to use me
Use this when:
- Reading product data from Google Sheets for the homepage
- Appending new products received via Telegram webhook
- Setting up or updating service account credentials
- Migrating between Sheets configurations
- Debugging sheet access issues

## Key patterns
- Credentials can be passed as inline JSON string (for Vercel env vars) or file path
- Use `gc.open_by_key(SPREADSHEET_ID)` to open the target spreadsheet
- Active worksheet: `worksheet = spreadsheet.sheet1`
- Append row: `worksheet.append_row([no, link, nama, harga, timestamp])`
- Read all data: `worksheet.get_all_records()` for dict-based access
- Handle empty cells gracefully (use defaults for optional fields)
