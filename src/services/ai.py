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


def _build_threads_prompt(name: str, price: str, link: str) -> str:
    """Build the prompt for Threads 'Spill di Reply' content generation."""
    return f"""Buat 1 thread perdebatan untuk produk ini.
Nama Produk: {name}
Harga: {price}
Link: {link}
Pilih SATU dari angle berikut secara acak: [Unpopular Opinion / Relatable Sambat / Merendahkan Produk Mahal].

Format JSON yang diharapkan:
{{
  "angle_type": "...",
  "post_1_caption": "...",
  "post_2_reply_cta": "... [Link]"
}}"""


THREADS_SYSTEM_PROMPT = """Kamu adalah seorang Social Media Specialist dan Affiliate Marketer di platform X/Threads. Tugasmu adalah membuat konten "Engagement Bait" berupa thread pendek (2 post) yang memicu perdebatan atau emosi netizen Indonesia.

Aturan penulisan:
1. Gunakan bahasa Indonesia sehari-hari, natural, dan campur dengan sedikit slang Gen-Z/Jaksel (misal: jujurly, fomo, mending, valid no debat, nder).
2. POST 1 (Post Utama): HARUS murni opini kontroversial, keluhan (sambat), atau opini melawan arus (unpopular opinion). JANGAN ADA indikasi jualan, rekomendasi, atau menyebutkan link sama sekali. Fokus 100% memancing emosi/reaksi. Maksimal 250 karakter.
3. POST 2 (Reply/Thread): Ini adalah tempat menaruh link. Buat transisi yang natural seolah-olah kamu merespons audiens atau sekadar "mumpung rame". Contoh angle Post 2: "Banyak yang nanya di DM...", "Biar kalian gak repot nyari...", atau "Sumpah gara-gara pake ini...".
4. DILARANG KERAS menggunakan hashtag (#) atau kata-kata iklan kaku.
5. Output HARUS dalam format JSON murni."""


async def generate_threads_content(
    name: str,
    price: str,
    link: str,
    max_retries: int = 3,
) -> dict:
    """Generate Threads 'Spill di Reply' content (Post 1 + Post 2).

    Returns dict with keys: angle_type, post_1_caption, post_2_reply_cta.
    Returns empty dict on failure.
    """
    if not settings.OPENROUTER_API_KEY:
        log.warning("OPENROUTER_API_KEY not set, skipping threads content generation")
        return {}

    user_prompt = _build_threads_prompt(name, price, link)

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
        max_retries=0,
    )

    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model="openrouter/free",
                messages=[
                    {"role": "system", "content": THREADS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                extra_headers={
                    "HTTP-Referer": "https://github.com/agungprsty/fanisantika",
                    "X-Title": "Affiliate Threads Generator",
                },
            )

            content = response.choices[0].message.content.strip() if response.choices[0].message.content else ""

            # Try to parse JSON from response
            import json as _json

            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = _json.loads(content)

            # Validate required keys
            if all(k in result for k in ("angle_type", "post_1_caption", "post_2_reply_cta")):
                # Enforce 250 char limit on post_1
                if len(result["post_1_caption"]) > 250:
                    result["post_1_caption"] = result["post_1_caption"][:247] + "..."
                log.info(f"Threads content generated for '{name}' (angle: {result['angle_type']})")
                return result
            else:
                log.warning("AI response missing required keys, retrying...")
                continue

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "502" in error_msg or "503" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    log.warning(f"Server busy/Rate limit. Waiting {wait_time}s (Attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                else:
                    log.error(f"Threads generation failed after {max_retries} attempts.")
                    return {}
            else:
                log.error(f"Threads generation failed: {error_msg}")
                return {}

    return {}