// Global State
let currentScope = 'Todas';
let currentSearch = '';
let currentGrants = [];
let userProfile = null;

// Initialize app on load
document.addEventListener('DOMContentLoaded', async () => {
  await loadProfile();
  await loadStats();
  await loadGrants();
});

// Toast Helper
function showToast(message, duration = 3000) {
  const toast = document.getElementById('toast');
  toast.innerText = message;
  toast.classList.remove('opacity-0', 'pointer-events-none', '-translate-y-2');
  toast.classList.add('opacity-100', 'translate-y-0');
  setTimeout(() => {
    toast.classList.add('opacity-0', 'pointer-events-none', '-translate-y-2');
    toast.classList.remove('opacity-100', 'translate-y-0');
  }, duration);
}

// Load User Profile
async function loadProfile() {
  try {
    const res = await fetch('/api/profile');
    if (!res.ok) return;
    userProfile = await res.json();

    // Update top header badge
    const badge = document.getElementById('top-profile-badge');
    if (badge) {
      badge.innerHTML = `<span>📍 ${userProfile.region}</span> &bull; <span>${userProfile.age_bracket}</span>`;
    }

    // Update form values
    const regionSelect = document.getElementById('profile-region');
    const ageSelect = document.getElementById('profile-age');
    const emailInput = document.getElementById('profile-email');
    const emailDisplay = document.getElementById('digest-email-display');

    if (regionSelect) regionSelect.value = userProfile.region;
    if (ageSelect) ageSelect.value = userProfile.age_bracket;
    if (emailInput) emailInput.value = userProfile.email || '';
    if (emailDisplay) emailDisplay.innerText = userProfile.email || 'No configurado aún';

  } catch (err) {
    console.error('Error al cargar perfil:', err);
  }
}

// Load Stats
async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const stats = await res.json();
    document.getElementById('stat-total').innerText = stats.total_grants;
    document.getElementById('stat-cv').innerText = stats.cv_grants;
  } catch (err) {
    console.error('Error stats:', err);
  }
}

// Fetch & Render Grants
async function loadGrants() {
  const container = document.getElementById('grants-container');
  try {
    let url = `/api/grants?scope=${encodeURIComponent(currentScope)}`;
    if (currentSearch) {
      url += `&search=${encodeURIComponent(currentSearch)}`;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error('Error al consultar convocatorias');
    currentGrants = await res.json();

    if (currentGrants.length === 0) {
      container.innerHTML = `
        <div class="text-center py-12 bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <p class="text-slate-400 text-xs">No se encontraron convocatorias con los filtros seleccionados.</p>
          <button onclick="setFilterScope('Todas')" class="mt-3 text-xs text-blue-400 font-semibold underline">
            Mostrar todas las ayudas
          </button>
        </div>
      `;
      return;
    }

    let html = '';
    currentGrants.forEach(g => {
      const match = g.match || { score: 75, reasons: [] };
      const scoreBadgeColor = match.score >= 85 ? 'text-emerald-400 border-emerald-500/30 bg-emerald-950/40' : 'text-blue-400 border-blue-500/30 bg-blue-950/40';
      const isSaved = g.bookmarked;

      let scopeColor = 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      if (g.scope === 'Autonómica') scopeColor = 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30';
      if (g.scope === 'Europea') scopeColor = 'bg-purple-500/20 text-purple-300 border-purple-500/30';

      const reasonsTags = (match.reasons || []).map(r => 
        `<span class="text-[10px] font-medium bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full border border-slate-700/80">${r}</span>`
      ).join('');

      html += `
        <div class="bg-slate-900/90 hover:bg-slate-900 border border-slate-800/80 hover:border-slate-700 rounded-2xl p-4 transition-all shadow-sm space-y-3">
          
          <!-- Header card -->
          <div class="flex items-start justify-between gap-2">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border ${scopeColor}">
                ${g.scope} &bull; ${g.region}
              </span>
              <span class="text-[10px] font-bold px-2 py-0.5 rounded-md border ${scoreBadgeColor}">
                ⚡ ${match.score}% Afinidad
              </span>
            </div>

            <button onclick="toggleBookmark('${g.id}', ${!isSaved})" title="${isSaved ? 'Guardada' : 'Guardar'}" class="p-1.5 rounded-lg text-slate-400 hover:text-amber-400 active:scale-90 transition-all">
              <svg class="w-5 h-5 ${isSaved ? 'text-amber-400 fill-amber-400' : 'fill-none'}" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"></path>
              </svg>
            </button>
          </div>

          <!-- Title & Entity -->
          <div>
            <h3 onclick="openGrantModal('${g.id}')" class="font-bold text-sm text-white hover:text-blue-400 cursor-pointer transition-colors leading-snug">
              ${g.title}
            </h3>
            <p class="text-[11px] text-slate-400 mt-1 line-clamp-1">
              🏛️ ${g.entity}
            </p>
          </div>

          <!-- Cuantía y plazo -->
          <div class="bg-slate-950/70 border border-slate-800/80 rounded-xl p-2.5 flex items-center justify-between text-xs">
            <div>
              <span class="text-[10px] text-slate-400 block">Cuantía</span>
              <span class="font-bold text-emerald-400 text-xs">${g.amount}</span>
            </div>
            <div class="text-right">
              <span class="text-[10px] text-slate-400 block">Plazo de solicitud</span>
              <span class="text-slate-300 text-[11px] font-medium">${g.deadline}</span>
            </div>
          </div>

          <!-- Match reasons tags -->
          <div class="flex flex-wrap gap-1">
            ${reasonsTags}
          </div>

          <!-- Actions -->
          <div class="pt-1 flex items-center space-x-2">
            <button onclick="openGrantModal('${g.id}')" class="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 py-2 rounded-xl text-xs font-semibold border border-slate-700/80 transition-all">
              Ver Requisitos
            </button>
            <a href="${g.official_url}" target="_blank" class="flex-1 bg-blue-600 hover:bg-blue-500 text-white py-2 rounded-xl text-xs font-semibold text-center transition-all shadow-md shadow-blue-600/20 flex items-center justify-center space-x-1">
              <span>Tramitar</span>
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
              </svg>
            </a>
          </div>

        </div>
      `;
    });

    container.innerHTML = html;

  } catch (err) {
    container.innerHTML = `<div class="text-center py-8 text-rose-400 text-xs">Error: ${err.message}</div>`;
  }
}

// Scope Filter Switcher
function setFilterScope(scope) {
  currentScope = scope;
  document.querySelectorAll('.filter-scope-btn').forEach(btn => {
    if (btn.dataset.scope === scope) {
      btn.className = 'filter-scope-btn px-3 py-1.5 rounded-full font-medium transition-all bg-blue-600 text-white';
    } else {
      btn.className = 'filter-scope-btn px-3 py-1.5 rounded-full font-medium transition-all bg-slate-800 text-slate-300 hover:bg-slate-700';
    }
  });
  loadGrants();
}

// Search debounce
let searchTimer = null;
function handleSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentSearch = document.getElementById('search-input').value;
    loadGrants();
  }, 250);
}

// Grant Details Modal
function openGrantModal(id) {
  const grant = currentGrants.find(g => g.id === id);
  if (!grant) return;

  document.getElementById('modal-scope-badge').innerText = `${grant.scope} • ${grant.region}`;
  document.getElementById('modal-title').innerText = grant.title;
  document.getElementById('modal-entity').innerText = grant.entity;
  document.getElementById('modal-amount').innerText = `💵 ${grant.amount}`;
  document.getElementById('modal-deadline').innerText = `⏳ ${grant.deadline}`;
  document.getElementById('modal-summary').innerText = grant.summary;
  document.getElementById('modal-requirements').innerText = grant.requirements;
  document.getElementById('modal-official-link').href = grant.official_url;

  const reasonsBox = document.getElementById('modal-reasons');
  const reasons = (grant.match && grant.match.reasons) || [];
  reasonsBox.innerHTML = reasons.map(r => 
    `<span class="bg-blue-950/70 border border-blue-800/80 text-blue-300 px-2.5 py-1 rounded-lg text-[11px] font-medium">${r}</span>`
  ).join('');

  document.getElementById('grant-modal').classList.remove('hidden');
}

function closeGrantModal() {
  document.getElementById('grant-modal').classList.add('hidden');
}

// Bookmark toggler
async function toggleBookmark(grantId, shouldSave) {
  try {
    const res = await fetch(`/api/bookmarks/${grantId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: shouldSave ? 'Guardada' : 'Eliminar' })
    });
    if (res.ok) {
      showToast(shouldSave ? '⭐ Añadida a tus guardadas' : '🗑️ Eliminada de guardadas');
      await loadGrants();
      await loadBookmarks();
      await loadStats();
    }
  } catch (err) {
    showToast('Error al actualizar guardados');
  }
}

// Load Bookmarks View
async function loadBookmarks() {
  const container = document.getElementById('saved-container');
  try {
    const res = await fetch('/api/bookmarks');
    if (!res.ok) return;
    const bookmarks = await res.json();

    if (bookmarks.length === 0) {
      container.innerHTML = `
        <div class="text-center py-12 bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <p class="text-slate-400 text-xs">No tienes convocatorias guardadas todavía.</p>
          <button onclick="switchTab('explore')" class="mt-3 text-xs text-blue-400 font-semibold underline">
            Explorar convocatorias disponibles
          </button>
        </div>
      `;
      return;
    }

    let html = '';
    bookmarks.forEach(b => {
      html += `
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div class="flex items-start justify-between">
            <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">
              ${b.scope} &bull; ${b.region}
            </span>
            <button onclick="toggleBookmark('${b.grant_id}', false)" class="text-slate-400 hover:text-rose-400 text-xs font-medium">
              Quitar
            </button>
          </div>

          <div>
            <h3 class="font-bold text-sm text-white leading-snug">${b.title}</h3>
            <p class="text-[11px] text-slate-400 mt-0.5">${b.entity}</p>
          </div>

          <div class="flex items-center justify-between text-xs text-slate-300 bg-slate-950 p-2 rounded-xl">
            <span>💵 <strong class="text-emerald-400">${b.amount}</strong></span>
            <span>⏳ ${b.deadline}</span>
          </div>

          <div class="flex items-center space-x-2 pt-1">
            <a href="${b.official_url}" target="_blank" class="w-full bg-blue-600 hover:bg-blue-500 text-white py-2 rounded-xl text-xs font-semibold text-center transition-all flex items-center justify-center space-x-1">
              <span>Tramitar Solicitud</span>
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
              </svg>
            </a>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (err) {
    console.error('Error al cargar bookmarks:', err);
  }
}

// Trigger Weekly Digest
async function triggerDigestGeneration() {
  try {
    showToast('Generando boletín semanal...');
    const res = await fetch('/api/digest/send', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(`✅ ${data.status}`);
      document.getElementById('digest-log-status').innerHTML = `
        <div class="space-y-1">
          <p class="text-emerald-400 font-semibold">✓ ${data.status}</p>
          <p class="text-[11px] text-slate-400">Destinatario: ${data.recipient}</p>
          <p class="text-[11px] text-slate-400">Total convocatorias incluidas: ${data.grants_count}</p>
        </div>
      `;
    }
  } catch (err) {
    showToast('Error al generar boletín');
  }
}

// Preview Digest in new tab
function previewLatestDigest() {
  window.open('/api/digest/latest', '_blank');
}

// Sync official sources
async function syncOfficialSources() {
  const icon = document.getElementById('sync-icon');
  icon.classList.add('animate-spin');
  try {
    const res = await fetch('/api/grants/sync', { method: 'POST' });
    const data = await res.json();
    showToast(`🔄 ${data.message}`);
    await loadGrants();
    await loadStats();
  } catch (err) {
    showToast('Error al sincronizar');
  } finally {
    icon.classList.remove('animate-spin');
  }
}

// Save Profile changes
async function saveProfile(e) {
  e.preventDefault();
  const region = document.getElementById('profile-region').value;
  const age_bracket = document.getElementById('profile-age').value;
  const email = document.getElementById('profile-email').value;

  const interests = [];
  if (document.getElementById('int-biz').checked) interests.push('autonomo', 'pyme');
  if (document.getElementById('int-dig').checked) interests.push('digitalizacion', 'innovacion');
  if (document.getElementById('int-edu').checked) interests.push('formacion', 'becas');
  if (document.getElementById('int-inno').checked) interests.push('idiomas', 'recualificacion');

  try {
    const res = await fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        region,
        age_bracket,
        user_types: ['autonomo', 'pyme', 'estudiante'],
        interests,
        email,
        notify_weekly: 1
      })
    });
    if (res.ok) {
      showToast('✅ Perfil y filtros actualizados');
      await loadProfile();
      await loadGrants();
      switchTab('explore');
    }
  } catch (err) {
    showToast('Error al guardar perfil');
  }
}

// Navigation Tab Switcher
function switchTab(tabName) {
  // Hide all sections
  document.getElementById('view-explore').classList.add('hidden');
  document.getElementById('view-saved').classList.add('hidden');
  document.getElementById('view-digest').classList.add('hidden');
  document.getElementById('view-profile').classList.add('hidden');

  // Show selected
  document.getElementById(`view-${tabName}`).classList.remove('hidden');

  // Update navigation buttons
  document.querySelectorAll('.nav-btn').forEach(btn => {
    if (btn.dataset.target === tabName) {
      btn.classList.add('text-blue-500', 'font-semibold');
      btn.classList.remove('text-slate-400');
    } else {
      btn.classList.remove('text-blue-500', 'font-semibold');
      btn.classList.add('text-slate-400');
    }
  });

  if (tabName === 'saved') loadBookmarks();
}
