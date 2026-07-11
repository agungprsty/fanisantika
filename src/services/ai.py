"""AI caption generation using OpenRouter API."""

import logging
import asyncio
from openai import AsyncOpenAI

from src.config import settings

log = logging.getLogger(__name__)


def _build_prompt(name: str, price: str, link: str, platform: str) -> str:
    """Build the prompt for caption generation."""
    lines = [
        "Buatkan caption Instagram/WhatsApp untuk produk affiliate ini:",
        f"- Nama: {name}",
        f"- Harga: {price}",
        f"- Platform: {platform}",
        f"- Link: {link}",
        "",
        "Gunakan gaya bahasa santai, emoji secukupnya (tidak terlalu banyak),",
        "dan sertakan CTA. Format yang bagus untuk posting affiliate.",
    ]
    return "\n".join(lines)


async def generate_caption(
    name: str,
    price: str,
    link: str,
    platform: str,
    max_retries: int = 3
) -> str:
    """Generate a product caption using OpenRouter (OpenAI SDK)."""
    
    if not settings.OPENROUTER_API_KEY:
        log.warning("OPENROUTER_API_KEY not set, skipping caption generation")
        return ""

    prompt = _build_prompt(name, price, link, platform)
    
    # Inisialisasi client AsyncOpenAI dengan max_retries=0
    # untuk mencegah badai request (retry storm) dari library bawaan
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
        max_retries=0, 
    )

    for attempt in range(max_retries):
        try:
            # Gunakan model openrouter/free untuk otomatis memilih model gratis yang tersedia
            response = await client.chat.completions.create(
                model="openrouter/free",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                extra_headers={
                    "HTTP-Referer": "https://github.com/agungprsty/fanisantika", 
                    "X-Title": "Affiliate Auto Caption", 
                }
            )
            
            caption = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
            log.info(f"Caption generated for '{name}' ({len(caption)} chars)")
            return caption
            
        except Exception as e:
            error_msg = str(e)
            # Tangkap error limit 429 atau error server lainnya untuk retry manual
            if "429" in error_msg or "502" in error_msg or "503" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3  # Jeda 3s, 6s...
                    log.warning(f"Server sibuk/Rate limit API. Menunggu {wait_time} detik (Percobaan {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                else:
                    log.error(f"Gagal generate caption setelah {max_retries} percobaan.")
                    return ""
            else:
                # Jika error fatal lain (seperti API key salah), langsung berhenti
                log.error(f"Caption generation failed: {error_msg}")
                return ""
                
    return ""