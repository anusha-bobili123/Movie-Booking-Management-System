/* public.js — Infinite Scroll + Filters + Smooth Animations */

const POSTER_POOL = [
  'https://image.tmdb.org/t/p/w500/1g0dhYtq4irTY1GPXvft6k4YLjm.jpg',
  'https://image.tmdb.org/t/p/w500/d5NXSklXo0qyIYkgV94XAgMIckC.jpg',
  'https://image.tmdb.org/t/p/w500/qNBAXBIQlnOThrVvA6mA2B5ggV6.jpg',
  'https://image.tmdb.org/t/p/w500/iuFNMS8vlzsH9RTiQFQnZXqiDf9.jpg',
  'https://image.tmdb.org/t/p/w500/8kNruSfhk5IoE4eZOc4UpvDn6tM.jpg',
  'https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg',
  'https://image.tmdb.org/t/p/w500/mDfJG3LC3Dqb67AZ52x3Z0jU0uB.jpg',
  'https://image.tmdb.org/t/p/w500/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg',
  'https://image.tmdb.org/t/p/w500/rktDFPbfHfUbArZ6OOOKsXcv0Bm.jpg',
  'https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg',
  'https://image.tmdb.org/t/p/w500/hO7KbdvGOtDdeg0W4Y5nKEHeDDh.jpg',
  'https://image.tmdb.org/t/p/w500/A3ZbZsmsvNGdprRi2lKgGEeVLEH.jpg',
  'https://image.tmdb.org/t/p/w500/xJHokMbljvjADYdit5fK5VQsXEG.jpg',
  'https://image.tmdb.org/t/p/w500/vZloFAK7NmvMGKE7VkF5UHaz0I.jpg',
  'https://image.tmdb.org/t/p/w500/jYEW5xZkZk2WTrdbMGAPFuBqbDc.jpg',
  'https://image.tmdb.org/t/p/w500/y3NkPMHBBnWbRNnEzBjQX3YJiGY.jpg',
  'https://image.tmdb.org/t/p/w500/8UlWHLMpgZm9bx6QYrbaiDwmaEL.jpg',
  'https://image.tmdb.org/t/p/w500/jpurJ9jAcLCYjgHHfYF32m3zJYm.jpg',
  'https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg',
  'https://image.tmdb.org/t/p/w500/udDclJoHjfjb8Ekgsd4FDteOkCU.jpg',
  'https://image.tmdb.org/t/p/w500/nkayOAUBUu4mMvyNf9iHSUiPjF1.jpg',
  'https://image.tmdb.org/t/p/w500/velWPhVMQeQKcxggNEU8YmIo52R.jpg',
  'https://image.tmdb.org/t/p/w500/d2JyDRPsXkJWA1lUHMHV37g5MrP.jpg',
  'https://image.tmdb.org/t/p/w500/7lyBcpYB0Qt8gYhXYaEZUNlMkn7.jpg',
  'https://image.tmdb.org/t/p/w500/wuMc08IPKEatf9rnMNXvIDxqP4W.jpg',
  'https://image.tmdb.org/t/p/w500/b3kdkeXfOGDHNMyIfnuC9172vNY.jpg',
  'https://image.tmdb.org/t/p/w500/5KCVkau1HEl7ZzSPeg1kHIX2i5e.jpg',
  'https://image.tmdb.org/t/p/w500/iiZZdoQBEYBv6id8su7ImL0oCbD.jpg',
  'https://image.tmdb.org/t/p/w500/6Wdl9N6dL0Hi5T4thkQnD0rMon9.jpg',
  'https://image.tmdb.org/t/p/w500/pFlaoHTZeyNkG83vxsAJiGzfSsa.jpg',
  'https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSligaOwTiz.jpg',
  'https://image.tmdb.org/t/p/w500/aQvJ5WPzZgYVDrxLX4R6cLJCEaQ.jpg',
  'https://image.tmdb.org/t/p/w500/fm6KqXpk3M2HVveHwCrBSSBaO0V.jpg',
  'https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsLegHQr4xM4A.jpg',
  'https://image.tmdb.org/t/p/w500/2CAL2433ZeIihfX1Hb2139CX0pW.jpg',
  'https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg',
  'https://image.tmdb.org/t/p/w500/ArAGM4cJHNtSAuLhMSAxEMjAjAK.jpg',
  'https://image.tmdb.org/t/p/w500/kdPMUMJzyYAc4roD52qavX0nLIC.jpg',
  'https://image.tmdb.org/t/p/w500/rSPw7tgCH9c6NqICZef4kZjFOQ5.jpg',
  'https://image.tmdb.org/t/p/w500/xDMIl84Qo5Tsu62c9DGWhmPI67A.jpg',
  'https://image.tmdb.org/t/p/w500/9l1eZiJHmhr5jIlthMdJN5WYoff.jpg',
  'https://image.tmdb.org/t/p/w500/e1mjopzAS2KNsvpbpahQ1a6SkSn.jpg',
  'https://image.tmdb.org/t/p/w500/8rpDcsfLJypbO6vREc0547VKqEv.jpg',
  'https://image.tmdb.org/t/p/w500/xBHvZcjRiWyobQ9kxBpkvURvDus.jpg',
  'https://image.tmdb.org/t/p/w500/74xTEgt7R36Fpooo50r9T25onhq.jpg',
  'https://image.tmdb.org/t/p/w500/ugZW8ocsrfgI95pnQ7wrmKDxIe.jpg',
  'https://image.tmdb.org/t/p/w500/5YZbUmjbMa3ClvSW1Wj3D6XGkVA.jpg',
  'https://image.tmdb.org/t/p/w500/vOipe2myi26UDwP978hsYOrnUWh.jpg',
  'https://image.tmdb.org/t/p/w500/tnAuB8sAhjqueIAQ6jd2M1AkFDc.jpg',
  'https://image.tmdb.org/t/p/w500/gPbM0MK8CP8A174rmUwGsADNYKD.jpg',
];


// ─── Filter / navigation ─────────────────────────────────────────────────────
function applyFilters(scrollToMovies) {
  const url = new URL('/', window.location.origin);
  const search = document.getElementById('searchInput')?.value.trim();
  const city   = document.getElementById('citySelect')?.value;
  const genre  = document.getElementById('genreSelect')?.value;
  const lang   = document.getElementById('langSelect')?.value;
  if (search) url.searchParams.set('search', search);
  if (city)   url.searchParams.set('city', city);
  if (genre)  url.searchParams.set('genre', genre);
  if (lang)   url.searchParams.set('language', lang);
  if (scrollToMovies) url.hash = 'movies-section';
  window.location.href = url.toString();
}

document.getElementById('searchInput')?.addEventListener('keyup', e => { if (e.key === 'Enter') applyFilters(true); });
document.getElementById('searchBtn')?.addEventListener('click', () => applyFilters(true));
document.getElementById('genreSelect')?.addEventListener('change', () => applyFilters(true));
document.getElementById('langSelect')?.addEventListener('change', () => applyFilters(true));

// Auto-scroll to movies section if hash present on page load
if (window.location.hash === '#movies-section') {
  setTimeout(() => {
    const el = document.getElementById('movies-section');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 300);
}

// ─── Card builder ─────────────────────────────────────────────────────────────
function buildMovieCard(m, cardIdx) {
  const poster = POSTER_POOL[cardIdx % POSTER_POOL.length];
  const shortTitle = m.title.length > 20 ? m.title.substring(0, 20) + '…' : m.title;
  const ratingBadge = m.rating != null
    ? `<div class="rating-badge"><i class="fas fa-star"></i>${Number(m.rating).toFixed(1)}</div>`
    : '';
  const langBadge = m.language
    ? `<div class="lang-badge">${escHtml(m.language)}</div>`
    : '';
  const cityRow = m.city
    ? `<div class="movie-city"><i class="fas fa-map-marker-alt me-1" style="color:#e50914;font-size:.7rem;"></i>${escHtml(m.city)}</div>`
    : '';
  const screenBadge = m.screen_number
    ? `<span class="movie-screen-badge">${escHtml(m.screen_number)}</span>`
    : '';
  const theatreRow = m.theatre_name
    ? `<div class="movie-theatre" title="${escHtml(m.theatre_location || '')}">
        <i class="fas fa-building me-1" style="color:#888;font-size:.65rem;"></i>
        <span>${escHtml(m.theatre_name)}</span>${screenBadge}
       </div>`
    : '';
  const genreTag = m.genre    ? `<span class="tag tag-genre">${escHtml(m.genre)}</span>` : '';
  const durTag   = m.duration ? `<span class="tag tag-dur">${m.duration}m</span>` : '';

  return `
    <a href="/movie/${encodeURIComponent(m.movie_id)}" class="movie-card-wrap text-decoration-none">
      <div class="movie-card movie-card-anim">
        <div class="movie-poster">
          <img src="${poster}" alt="${escHtml(m.title)}" loading="lazy" decoding="async"
               onload="this.closest('.movie-poster').classList.add('img-ready')"
               onerror="this.closest('.movie-poster').classList.add('img-ready');this.style.display='none';this.nextElementSibling.style.display='flex'">
          <div class="fallback-poster" style="display:none">
            <i class="fas fa-film"></i>
            <span>${escHtml(shortTitle)}</span>
          </div>
          ${ratingBadge}
          ${langBadge}
        </div>
        <div class="movie-body">
          <div class="movie-title" title="${escHtml(m.title)}">${escHtml(m.title)}</div>
          ${cityRow}
          ${theatreRow}
          <div class="movie-tags">${genreTag}${durTag}</div>
        </div>
      </div>
    </a>`;
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─── Card entrance animation ──────────────────────────────────────────────────
function animateCards(cards) {
  cards.forEach((card, i) => {
    // Set staggered animation delay via CSS custom property
    const delay = Math.min(i * 0.04, 0.35);
    card.style.animationDelay = delay + 's';
    // Handle cached images
    const img = card.querySelector('.movie-poster img');
    if (img && img.complete && img.naturalWidth > 0) {
      img.closest('.movie-poster').classList.add('img-ready');
    }
  });
}

// ─── Infinite scroll logic ────────────────────────────────────────────────────
function buildApiUrl(page) {
  const s = window.MOVIE_SCROLL;
  const url = new URL('/api/movies', window.location.origin);
  url.searchParams.set('page', page);
  if (s.genre)    url.searchParams.set('genre', s.genre);
  if (s.language) url.searchParams.set('language', s.language);
  if (s.city)     url.searchParams.set('city', s.city);
  if (s.search)   url.searchParams.set('search', s.search);
  return url.toString();
}

async function loadNextPage() {
  const s = window.MOVIE_SCROLL;
  if (s.loading || !s.hasMore) return;
  s.loading = true;

  const loader = document.getElementById('moviesLoader');
  if (loader) loader.style.display = 'block';

  try {
    const nextPage = s.currentPage + 1;
    const res = await fetch(buildApiUrl(nextPage));
    if (!res.ok) throw new Error('Network error');
    const data = await res.json();

    const grid = document.getElementById('moviesGrid');
    if (grid && data.movies && data.movies.length) {
      const tempDiv = document.createElement('div');
      data.movies.forEach(m => {
        tempDiv.insertAdjacentHTML('beforeend', buildMovieCard(m, s.cardIndex++));
      });
      const newCards = Array.from(tempDiv.querySelectorAll('.movie-card'));
      while (tempDiv.firstChild) grid.appendChild(tempDiv.firstChild);
      animateCards(newCards);
    }

    s.currentPage = data.page;
    s.hasMore = data.has_more;

    if (!s.hasMore) {
      const endEl = document.getElementById('moviesEnd');
      if (endEl) endEl.style.display = 'block';
      const sentinel = document.getElementById('infiniteScrollSentinel');
      if (sentinel) scrollObserver.unobserve(sentinel);
    }
  } catch (err) {
    console.error('Failed to load more movies:', err);
  } finally {
    s.loading = false;
    const loader = document.getElementById('moviesLoader');
    if (loader) loader.style.display = 'none';
  }
}

// Observer watches the sentinel div — triggers 800px before it enters viewport for pre-loading
const scrollObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) loadNextPage();
  });
}, { rootMargin: '800px' });

document.addEventListener('DOMContentLoaded', () => {
  const sentinel = document.getElementById('infiniteScrollSentinel');
  if (sentinel) {
    if (window.MOVIE_SCROLL?.hasMore) {
      scrollObserver.observe(sentinel);
    } else {
      const endEl = document.getElementById('moviesEnd');
      if (endEl && window.MOVIE_SCROLL?.total > 0) endEl.style.display = 'block';
    }
  }

  // Animate SSR-rendered cards with IntersectionObserver
  const cardObserver = new IntersectionObserver(entries => {
    entries.forEach(en => {
      if (en.isIntersecting) {
        en.target.classList.add('movie-card-anim');
        cardObserver.unobserve(en.target);
      }
    });
  }, { threshold: 0.06 });

  document.querySelectorAll('.movie-card').forEach((c, i) => {
    // Set stagger delay but don't apply animation yet (observer does it)
    c.style.animationDelay = Math.min(i * 0.025, 0.3) + 's';
    cardObserver.observe(c);
    // Handle already-cached images (onload won't fire for cached imgs)
    const img = c.querySelector('.movie-poster img');
    if (img && img.complete && img.naturalWidth > 0) {
      img.closest('.movie-poster').classList.add('img-ready');
    }
  });
});

// ─── Live search suggestions ───────────────────────────────────────────────────
const searchInput = document.getElementById('searchInput');
let suggestBox   = null;
let suggestTimer = null;

function createSuggestBox() {
  if (suggestBox) return suggestBox;
  suggestBox = document.createElement('div');
  suggestBox.id = 'searchSuggestBox';
  suggestBox.style.cssText = `
    position:absolute; top:calc(100% + 8px); left:0; right:0; z-index:9998;
    background:#13131a; border:1px solid rgba(255,255,255,0.12);
    border-radius:12px; box-shadow:0 12px 40px rgba(0,0,0,0.6);
    overflow:hidden; display:none;
  `;
  const wrap = searchInput.closest('.hero-search');
  if (wrap) { wrap.style.position = 'relative'; wrap.appendChild(suggestBox); }
  return suggestBox;
}

searchInput?.addEventListener('input', () => {
  clearTimeout(suggestTimer);
  const q = searchInput.value.trim();
  if (q.length < 2) { hideSuggestions(); return; }
  suggestTimer = setTimeout(() => fetchSuggestions(q), 250);
});
searchInput?.addEventListener('blur', () => setTimeout(hideSuggestions, 200));

function hideSuggestions() {
  const box = document.getElementById('searchSuggestBox');
  if (box) box.style.display = 'none';
}

function fetchSuggestions(q) {
  fetch(`/search-suggestions?q=${encodeURIComponent(q)}`)
    .then(r => r.json())
    .then(data => showSuggestions(data, q))
    .catch(() => {});
}

function showSuggestions(data, q) {
  const box = createSuggestBox();
  box.innerHTML = '';
  if (!data || (!data.movies?.length && !data.genres?.length)) { hideSuggestions(); return; }
  let html = '';
  if (data.genres?.length) {
    html += `<div style="padding:8px 14px 4px;font-size:.7rem;color:rgba(255,255,255,.4);letter-spacing:.08em;font-weight:600;">GENRES</div>`;
    data.genres.forEach(g => {
      html += `<div class="suggest-item" onclick="pickSuggestion('genre','${g.replace(/'/g,"\\'")}')"><i class="fas fa-tags" style="color:#e50914;margin-right:8px;font-size:.8rem;"></i><span>${g}</span></div>`;
    });
  }
  if (data.movies?.length) {
    html += `<div style="padding:8px 14px 4px;font-size:.7rem;color:rgba(255,255,255,.4);letter-spacing:.08em;font-weight:600;">MOVIES</div>`;
    data.movies.forEach(m => {
      html += `<div class="suggest-item" onclick="pickSuggestion('movie','${m.title.replace(/'/g,"\\'")}')"><i class="fas fa-film" style="color:rgba(255,255,255,.4);margin-right:8px;font-size:.8rem;"></i><span>${m.title}</span><span style="margin-left:auto;font-size:.75rem;color:rgba(255,255,255,.35);">${m.genre||''}</span></div>`;
    });
  }
  box.innerHTML = html + `<style>.suggest-item{display:flex;align-items:center;padding:10px 14px;cursor:pointer;color:rgba(255,255,255,.85);font-size:.88rem;transition:background .15s;}.suggest-item:hover{background:rgba(229,9,20,.15);}</style>`;
  box.style.display = 'block';
}

function pickSuggestion(type, value) {
  if (type === 'genre') {
    const gs = document.getElementById('genreSelect');
    if (gs) { gs.value = value; searchInput.value = ''; }
    else searchInput.value = value;
  } else {
    searchInput.value = value;
  }
  hideSuggestions();
  applyFilters(true);
}
