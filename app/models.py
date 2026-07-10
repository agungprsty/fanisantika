"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field


class Product(BaseModel):
    """Represents a single product entry."""

    no: int
    link: str
    nama: str = ""
    harga: str = ""
    timestamp: str = ""


class TelegramMessage(BaseModel):
    """Parsed message from Telegram webhook."""

    text: str = Field(default="")
    chat_id: str = Field(default="")


class WebhookResponse(BaseModel):
    """Response sent back to Telegram."""

    method: str = "sendMessage"
    chat_id: str = ""
    text: str = ""
    parse_mode: str | None = "HTML"
