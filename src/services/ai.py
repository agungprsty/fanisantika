"""AI caption generation using OpenRouter API."""

import logging
import asyncio
from google import genai
from google.genai import types

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
    """Generate a product caption using Gemini API."""
    
    if not settings.GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY not set, skipping caption generation")
        return ""

    prompt = _build_prompt(name, price, link, platform)
    
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt
            )
            caption = response.text.strip() if response.text else ""
            
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
            else:
                log.error(f"Gagal generate caption: {error_msg}")
                break
    return ""


def _build_threads_prompt(name: str, description: str, price: str, link: str, hook_database_json: str) -> str:
    """Build the prompt for Threads 'H-P-S-C' content generation."""
    return f"""Buat 3 postingan berseri (Threads) untuk produk ini.
Nama Produk: {name}
Deskripsi/Fungsi: {description}
Harga: {price}
Link/Bio: {link}

REFERENSI HOOK DATABASE:
{hook_database_json}

Tugasmu:
1. Analisis 'Deskripsi/Fungsi' produk di atas.
2. Pilih SATU `hook_type` dari referensi hook database yang paling relevan.
3. Gunakan salah satu `examples` dari `hook_type` tersebut sebagai kalimat pembuka yang MUTLAK di Post 1.
4. Buat 3 post sesuai formula H-P-S-C.

Format JSON yang diwajibkan:
[
  {{ "post": 1, "content": "[Teks Hook dari database + Konteks/Validasi Masalah]" }},
  {{ "post": 2, "content": "[Teks Solusi Produk tanpa klaim hiperbola]" }},
  {{ "post": 3, "content": "[Teks Kesimpulan + CTA ke Link/Bio]" }}
]"""


THREADS_SYSTEM_PROMPT = """Kamu adalah seorang AI Affiliate Copywriter spesialis platform Threads.
Tugas utamamu adalah meracik konten promosi berseri (3 postingan berurutan) yang natural, empatik, tidak manipulatif, dan sangat beresonansi dengan pola pikir rasional calon pembeli.

PANDUAN OPERASIONAL (FORMULA H-P-S-C):
- Post 1 (Hook + Context): Mulai dengan kalimat Hook yang dipilih dari referensi untuk menghentikan scroll audiens. Lanjutkan dengan 1-2 kalimat yang memvalidasi masalah harian agar audiens merasa dipahami. JANGAN menyebutkan nama produk di post ini. Maksimal 280 karakter.
- Post 2 (Solution / Value): Hadirkan produk secara halus sebagai solusi rasional. Jelaskan 1-2 fungsi krusial atau real experience tanpa menggunakan klaim hiperbola, kata sifat berlebihan, atau kesan "hard selling".
- Post 3 (Call to Action): Berikan penutup singkat yang meyakinkan, diakhiri dengan arahan lembut menuju link afiliasi atau bio.

GAYA BAHASA (TONE & VOICE):
Gunakan gaya bahasa santai, kasual (gue/lo atau aku/kamu), informatif, dan storytelling. 
Hindari bahasa robotik, jangan gunakan hashtag (#), dan jangan terkesan seperti iklan tradisional.

ATURAN OUTPUT:
Kamu HANYA diizinkan mengeluarkan output MURNI dalam format JSON (Array of Objects) sesuai struktur yang diminta. Jangan tambahkan teks markdown, penjelasan, atau basa-basi di luar JSON array tersebut."""


async def generate_threads_content(
    name: str,
    description: str,
    price: str,
    link: str,
    max_retries: int = 3,
) -> list:
    """Generate Threads H-P-S-C content (3 posts).

    Returns a list of dicts: [{"post": 1, "content": "..."}, ...]
    Returns empty list on failure.
    """
    if not settings.GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY not set, skipping threads content generation")
        return []

    # Load hook database
    import json as _json
    import os
    
    hook_database_json = "[]"
    try:
        hook_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hook_databases.json")
        with open(hook_path, "r", encoding="utf-8") as f:
            hook_database_json = f.read()
    except Exception as e:
        log.error(f"Gagal memuat hook_databases.json: {e}")

    user_prompt = _build_threads_prompt(name, description, price, link, hook_database_json)

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model='gemini-3.6-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=THREADS_SYSTEM_PROMPT,
                )
            )
            content = response.text.strip() if response.text else ""

            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = _json.loads(content)

            # Validate required format: list of 3 objects with "post" and "content"
            if isinstance(result, list) and len(result) >= 3:
                is_valid = True
                for i in range(3):
                    if "post" not in result[i] or "content" not in result[i]:
                        is_valid = False
                        break
                
                if is_valid:
                    log.info(f"Threads content generated for '{name}' (3 posts)")
                    return result[:3]  # Ensure exactly 3 posts are returned
                
            log.warning("AI response structure is not a valid 3-post array, retrying...")
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
                return []

    return []