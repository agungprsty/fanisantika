---
name: telegram-webhook
description: Handle Telegram bot webhook integration — parse incoming messages, validate input, and trigger downstream actions
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: messaging-integration
---

## What I do
- Set up Telegram webhook endpoint (`POST /webhook`)
- Parse incoming message formats (e.g., `link, nama, harga`)
- Validate required fields and handle optional ones gracefully
- Reply confirmation messages back to Telegram
- Handle edge cases (malformed input, missing link, duplicate saves)

## When to use me
Use this when working with Telegram bot integrations:
- Implementing or modifying the `/webhook` route
- Parsing and validating message formats
- Setting up the Telegram bot token from env vars
- Adding reply logic for user feedback
- Debugging webhook delivery issues (use `--reload` to test locally)

## Key patterns
- Webhook receives JSON via POST — use FastAPI's `Request.form()` or parse body
- Message format: comma-separated fields (link required, others optional)
- Always return 200 OK so Telegram doesn't retry
- Log incoming messages for debugging
- Reply to user with confirmation including saved data
