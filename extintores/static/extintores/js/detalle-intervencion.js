// Filtro de tarjetas (si el campo existe en esta versión del template).
const filterInput = document.getElementById('filterInput');
if (filterInput) {
    filterInput.addEventListener('keyup', function () {
        const value = this.value.toLowerCase();
        document.querySelectorAll('.card').forEach(card => {
            card.style.display = card.innerText.toLowerCase().includes(value) ? '' : 'none';
        });
    });
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function scrollToBottom() {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}

function scrollDown() {
    window.scrollBy({ top: window.innerHeight * 0.8, behavior: 'smooth' });
}

function scrollUp() {
    window.scrollBy({ top: -window.innerHeight * 0.8, behavior: 'smooth' });
}

// Galería: las miniaturas son livianas. La foto original se carga solo al abrirla.
const galleryItems = Array.from(document.querySelectorAll('.js-gallery-item'));
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightbox-img');
const lightboxCaption = document.getElementById('lightbox-caption');
const lightboxClose = document.getElementById('lightbox-close');
const lightboxPrev = document.getElementById('lightbox-prev');
const lightboxNext = document.getElementById('lightbox-next');
let currentImageIndex = -1;

function showLightboxImage(index) {
    if (!galleryItems.length || !lightbox || !lightboxImg || !lightboxCaption) {
        return;
    }

    currentImageIndex = (index + galleryItems.length) % galleryItems.length;
    const item = galleryItems[currentImageIndex];
    const fullUrl = item.dataset.fullUrl;
    const caption = item.dataset.caption || '';

    // Solo aquí se solicita la fotografía original de alta resolución.
    lightboxImg.src = fullUrl;
    lightboxImg.alt = caption;
    lightboxCaption.textContent = caption;
    lightbox.style.display = 'flex';
    lightbox.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    if (!lightbox || !lightboxImg) {
        return;
    }

    lightbox.style.display = 'none';
    lightbox.setAttribute('aria-hidden', 'true');
    lightboxImg.src = '';
    lightboxImg.alt = '';
    document.body.style.overflow = '';
    currentImageIndex = -1;
}

function changeImage(step) {
    if (currentImageIndex < 0 || !galleryItems.length) {
        return;
    }
    showLightboxImage(currentImageIndex + step);
}

galleryItems.forEach((item, index) => {
    item.addEventListener('click', () => showLightboxImage(index));
    item.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            showLightboxImage(index);
        }
    });
});

if (lightboxClose) {
    lightboxClose.addEventListener('click', closeLightbox);
}

if (lightboxPrev) {
    lightboxPrev.addEventListener('click', () => changeImage(-1));
}

if (lightboxNext) {
    lightboxNext.addEventListener('click', () => changeImage(1));
}

if (lightbox) {
    lightbox.addEventListener('click', event => {
        if (event.target === lightbox) {
            closeLightbox();
        }
    });
}

document.addEventListener('keydown', event => {
    if (!lightbox || lightbox.style.display !== 'flex') {
        return;
    }

    if (event.key === 'Escape') {
        closeLightbox();
    } else if (event.key === 'ArrowLeft') {
        changeImage(-1);
    } else if (event.key === 'ArrowRight') {
        changeImage(1);
    }
});
