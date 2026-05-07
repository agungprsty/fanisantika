# 💗 Affiliate Katalog

Katalog produk affiliate yang ringan, cepat, dan estetik. Dibangun dengan fokus pada performa dan kemudahan manajemen data melalui Google Sheets.

## 🚀 Fitur Utama

-   **Backend via Google Sheets**: Manajemen data produk langsung dari spreadsheet tanpa perlu database rumit.
-   **Tailwind CSS v4**: Menggunakan versi terbaru Tailwind untuk styling yang modern dan efisien.
-   **Stale-While-Revalidate Caching**: Data disimpan di `localStorage` selama 10 menit untuk pemuatan instan, namun tetap diperbarui secara otomatis di latar belakang.
-   **High Performance**: Proses build menggunakan minifikasi HTML, CSS (Purge), dan JS (Terser).
-   **SEO & Social Ready**: Dilengkapi dengan Open Graph tags dan favicon SVG yang ringan.

## 🛠️ Stack Teknologi

-   **Frontend**: HTML5, Tailwind CSS v4, Vanilla JavaScript.
-   **Tools**: NPM, Terser (JS Minifier), HTML-Minifier-Terser, PostCSS.
-   **Database**: Google Sheets API (via Google Apps Script).
-   **Deployment**: GitHub Pages via GitHub Actions.

## 📦 Struktur Folder

```text
affiliate-katalog/
├── .github/workflows/   # Otomatisasi deployment ke GitHub Pages
├── dist/                # File hasil produksi (Minified)
├── src/                 # Source code utama
│   ├── input.css        # Tailwind source
│   ├── app.js           # Logika caching & fetch
│   └── index.html       # Struktur utama
├── package.json         # Skrip build & dependensi
└── tailwind.config.js   # Konfigurasi Tailwind
```

## ⚙️ Pengembangan Lokal
Clone repositori:

```bash
git clone [https://github.com/agungprsty/fanisantika.git](https://github.com/agungprsty/fanisantika.git)
cd fanisantika
```

Instal dependensi:

```bash
npm install
```

Jalankan mode pengembangan (Watch):

```bash
npm run dev
```
Build untuk produksi:

```bash
npm run prod
```

## 🔄 Konfigurasi Cache
Sistem menggunakan localStorage dengan durasi 10 menit untuk menyeimbangkan antara kecepatan akses dan kesegaran data:

```javaScript

const CACHE_EXPIRY = 10 * 60 * 1000;
```

## 🚢 Deployment
Proyek ini terintegrasi dengan GitHub Actions. Setiap kali Anda melakukan push ke branch main, workflow akan otomatis:

1. Menjalankan npm run prod.
2. Mendorong isi folder dist ke branch gh-pages.
3. Memperbarui situs secara otomatis di GitHub Pages.
