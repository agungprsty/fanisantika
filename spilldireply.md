Ini strategi yang sangat brilian dan terbukti jauh lebih efektif dibandingkan menggabungkan semuanya di *post* pertama. Dalam dunia *affiliate* X (Twitter) dan Threads, teknik ini sering disebut sebagai **"Spill di Reply"**.

Ada dua alasan teknis dan psikologis mengapa pemisahan ini sangat tepat:

1. **Menghindari Hukuman Algoritma (Reach Penalty):** Algoritma X dan Threads cenderung membatasi distribusi atau *reach* sebuah *post* utama yang mengandung tautan eksternal (karena platform tidak ingin penggunanya keluar dari aplikasi). Dengan menaruh *link* di *reply*, *post* utama (Post 1) akan dianggap sebagai teks organik biasa sehingga bisa mendapatkan impresi maksimal.
2. **Menciptakan Ilusi Organik:** Pengguna internet sekarang sangat anti-iklan (*ad-blindness*). Jika mereka melihat *link* di *post* pertama, mereka akan langsung *scroll*. Jika *post* pertama hanya berisi opini murni, mereka akan terpancing untuk membaca, berdebat, atau membalas. Saat mereka membuka *thread* tersebut, baru mereka terpapar tautan afiliasi di *reply*.

Untuk mengakomodasi *flow* ini, kita perlu merombak *prompt* AI-nya. AI harus bisa menghasilkan dua *output* teks yang memiliki benang merah, tapi dengan *tone* yang berbeda.

Berikut adalah *prompt* yang sudah disesuaikan untuk menghasilkan format *Thread* (Post 1 & Post 2):

### System Prompt (Konteks Utama)

```text
Kamu adalah seorang Social Media Specialist dan Affiliate Marketer di platform X/Threads. Tugasmu adalah membuat konten "Engagement Bait" berupa thread pendek (2 post) yang memicu perdebatan atau emosi netizen Indonesia.

Aturan penulisan:
1. Gunakan bahasa Indonesia sehari-hari, natural, dan campur dengan sedikit slang Gen-Z/Jaksel (misal: jujurly, fomo, mending, valid no debat, nder).
2. POST 1 (Post Utama): HARUS murni opini kontroversial, keluhan (sambat), atau opini melawan arus (unpopular opinion). JANGAN ADA indikasi jualan, rekomendasi, atau menyebutkan link sama sekali. Fokus 100% memancing emosi/reaksi. Maksimal 250 karakter.
3. POST 2 (Reply/Thread): Ini adalah tempat menaruh link. Buat transisi yang natural seolah-olah kamu merespons audiens atau sekadar "mumpung rame". Contoh angle Post 2: "Banyak yang nanya di DM...", "Biar kalian gak repot nyari...", atau "Sumpah gara-gara pake ini...".
4. DILARANG KERAS menggunakan hashtag (#) atau kata-kata iklan kaku.
5. Output HARUS dalam format JSON murni.

```

### User Prompt (Data Dinamis)

```text
Buat 1 thread perdebatan untuk produk ini.
Nama Produk: {{nama_produk}}
Kategori: {{kategori_produk}}
Pilih SATU dari angle berikut secara acak: [Unpopular Opinion / Relatable Sambat / Merendahkan Produk Mahal].

Format JSON yang diharapkan:
{
  "angle_type": "...",
  "post_1_caption": "...",
  "post_2_reply_cta": "... [Link]"
}

```