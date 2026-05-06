// Konfigurasi API
const SHEET_API_URL = "https://script.google.com/macros/s/AKfycbwTrwM45sW0gQx634k2jIH7YSeJAd6staJ8hkMXPA-T8VKeDj-VbXofm6P9Mhb7vsHJow/exec";

// State Management
let allProducts = [];
let filteredProducts = [];
let displayedCount = 10;
const itemsPerLoad = 10;

// DOM Elements
const container = document.getElementById('linksContainer');
const loader = document.getElementById('loading');
const searchInput = document.getElementById('searchInput');
const loadMoreBtn = document.getElementById('loadMoreBtn');
const loadMoreContainer = document.getElementById('loadMoreContainer');

/**
 * Mengambil data dari Google Sheets
 */
async function fetchProducts() {
    try {
        const response = await fetch(SHEET_API_URL);
        const data = await response.json();
        
        // Transform data: Tambahkan No urut (displayId)
        allProducts = data.map((item, index) => ({
            ...item,
            noIndex: String(index + 1).padStart(2, '0')
        }));
        
        filteredProducts = allProducts;
        renderProducts();
    } catch (error) {
        console.error("Gagal memuat produk:", error);
        container.innerHTML = `<p class="text-center text-rose-400 py-10 text-xs italic">Koneksi gagal atau data tidak ditemukan.</p>`;
    } finally {
        loader.classList.add('hidden');
    }
}

/**
 * Merender daftar produk ke DOM
 * @param {boolean} append - Jika true, akan menambahkan data tanpa menghapus konten lama
 */
function renderProducts(append = false) {
    if (!append) {
        container.innerHTML = '';
        displayedCount = itemsPerLoad;
    }
    
    const currentItems = filteredProducts.slice(append ? displayedCount - itemsPerLoad : 0, displayedCount);

    if (filteredProducts.length === 0) {
        container.innerHTML = `<p class="text-center text-rose-300 py-10 text-xs italic">Produk tidak ditemukan...</p>`;
        loadMoreContainer.classList.add('hidden');
        return;
    }

    // Gunakan DocumentFragment untuk optimasi performa render
    const fragment = document.createDocumentFragment();

    currentItems.forEach((product) => {
        const a = document.createElement('a');
        a.href = product.link;
        a.target = "_blank";
        a.className = "group flex items-center py-6 border-b border-black/5 hover:bg-white/30 transition-all duration-300 px-2 rounded-lg";
        
        a.innerHTML = `
            <div class="w-12 flex-shrink-0 text-center">
                <span class="text-rose-700 italic font-medium text-lg group-hover:scale-110 inline-block transition-transform">
                    ${product.noIndex}
                </span>
            </div>
            <div class="h-10 w-[1px] bg-black/10 mx-4"></div>
            <div class="flex-grow">
                <h2 class="text-rose-800 font-bold text-[13px] sm:text-sm uppercase tracking-wider group-hover:translate-x-1 transition-transform duration-300">
                    ${product.name} 
                    <span class="ml-2 font-normal text-rose-400">${product.price}</span>
                </h2>
            </div>
            <div class="text-rose-200 group-hover:text-rose-500 transition-colors px-2">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
            </div>
        `;
        fragment.appendChild(a);
    });

    container.appendChild(fragment);

    // Tampilkan tombol Load More jika masih ada sisa data
    if (displayedCount < filteredProducts.length) {
        loadMoreContainer.classList.remove('hidden');
    } else {
        loadMoreContainer.classList.add('hidden');
    }
}

// Event: Klik Load More
loadMoreBtn.addEventListener('click', () => {
    displayedCount += itemsPerLoad;
    renderProducts(true);
});

// Event: Pencarian Responsif (By No atau Name)
searchInput.addEventListener('input', (e) => {
    const keyword = e.target.value.toLowerCase().trim();
    
    filteredProducts = allProducts.filter(p => 
        p.noIndex.includes(keyword) || 
        p.name.toLowerCase().includes(keyword)
    );
    
    renderProducts();
});

// Inisialisasi awal saat halaman dimuat
window.addEventListener('DOMContentLoaded', fetchProducts);