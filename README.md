# 💗 Affiliate Katalog

Katalog produk affiliate dengan FastAPI backend — menerima data via Telegram bot dan menyimpannya di Google Sheets.

## 🚀 Fitur Utama

- **Telegram Bot Webhook**: Kirim produk lewat chat, langsung tersimpan di Google Sheets
- **FastAPI Backend**: REST API cepat dengan Pydantic validation
- **Google Sheets Storage**: Data produk tersimpan rapi tanpa database tambahan
- **Jinja2 Templates**: Homepage yang ringan dan SEO-friendly
- **Vercel Serverless**: Deploy mudah tanpa server management

## 🛠️ Stack Teknologi

- **Backend**: FastAPI, Python 3.10+, Pydantic v2
- **Database**: Google Sheets (via gspread + service account)
- **Frontend**: Jinja2 Templates + Tailwind CSS
- **Deployment**: Vercel Serverless

## 📦 Struktur Folder

```text
affiliate-katalog/
├── app/                   # FastAPI application
│   ├── main.py            # Entry point + routes
│   ├── models.py          # Pydantic models
│   ├── config.py          # Environment settings
│   ├── services/          # Business logic
│   │   ├── telegram.py    # Webhook handler
│   │   └── sheets.py      # Google Sheets CRUD
│   └── templates/         # Jinja2 HTML templates
├── api/                   # Vercel serverless entry
│   └── index.py
├── .opencode/skills/      # OpenCode agent skills
├── vercel.json            # Vercel configuration
├── requirements.txt       # Python dependencies
└── AGENTS.md              # Project conventions
```

## ⚙️ Setup Lokal

1. Clone repositori:
```bash
git clone https://github.com/agungprsty/fanisantika.git
cd fanisantika
```

2. Buat virtual environment dan install dependensi:
```bash
python -m venv venv
source venv/bin/activate  # atau venv\Scripts\activate di Windows
pip install -r requirements.txt
```

3. Setup environment variables:
```bash
cp .env.example .env
# Edit .env dan isi:
#   TELEGRAM_BOT_TOKEN    — dari @BotFather
#   GOOGLE_SHEETS_CREDENTIALS — JSON service account Google
#   SPREADSHEET_ID        — ID spreadsheet Anda
```

4. Jalankan server:
```bash
uvicorn app.main:app --reload --port 8000
```

5. Buka `http://localhost:8000` untuk melihat homepage.

## 📱 Format Pesan Telegram

Kirim pesan ke bot dengan format:
```
link, nama (opsional), harga (opsional)
```

Contoh:
- `https://shopee.co.id/x/123` → link saja
- `https://shopee.co.id/x/123, Serum Wajah` → link + nama
- `https://shopee.co.id/x/123, Serum Wajah, 45000` → lengkap

## 🗄️ Google Sheets Structure

| No | Link | Nama | Harga | Timestamp |
|----|------|------|-------|-----------|
| 1 | https://... | Serum Wajah | 45000 | 2026-07-09T... |

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Homepage (Jinja2 template) |
| POST | `/webhook` | Telegram webhook endpoint |
| GET | `/api/products` | JSON API untuk semua produk |

## 🚢 Deployment ke Vercel

```bash
# Install CLI jika belum
npm i -g vercel

# Deploy
vercel deploy --prod
```

Pastikan `vercel.json` dan `api/index.py` sudah ada.

## 🔧 Mengkonfigurasi Google Sheets

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat service account baru, download JSON credentials
3. Copy isi JSON ke `.env` sebagai `GOOGLE_SHEETS_CREDENTIALS` (atau gunakan file path)
4. Share spreadsheet ke email service account
5. Salin Spreadsheet ID dari URL: `docs.google.com/spreadsheets/d/{ID}/edit`

## 🤖 Mengkonfigurasi Telegram Bot

1. Buka @BotFather di Telegram
2. Kirim `/newbot`, ikuti instruksi
3. Salin token bot ke `.env` sebagai `TELEGRAM_BOT_TOKEN`
4. Set webhook:
```bash
curl -X POST "https://api.telegram.org/bot{TOKEN}/setWebhook?url={YOUR_VERCEL_URL}/webhook"
```

## 📚 Development

- **Skills**: Lihat `.opencode/skills/` untuk instructions yang bisa dimuat oleh OpenCode agent.
- **Rules**: Baca `AGENTS.md` untuk konvensi penulisan kode dan struktur project.
- **Testing webhook lokal**: Gunakan [ngrok](https://ngrok.com/) atau [localtunnel](https://github.com/localtunnel/localtunnel) untuk expose port ke internet.
