const searchBtn = document.getElementById('search-btn');
const searchOverlay = document.getElementById('search-overlay');
const searchInput = document.getElementById('search-input');

searchBtn.addEventListener('click', () => {
    searchOverlay.classList.add('active');
    searchInput.focus(); // فوکوس خودکار
});

searchOverlay.addEventListener('click', (event) => {
    // بستن پاپ‌آپ با کلیک در خارج از باکس جستجو
    if (event.target === searchOverlay) {
        searchOverlay.classList.remove('active');
    }
});

// بستن پاپ‌آپ با فشردن دکمه Escape
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && searchOverlay.classList.contains('active')) {
        searchOverlay.classList.remove('active');
    }
});