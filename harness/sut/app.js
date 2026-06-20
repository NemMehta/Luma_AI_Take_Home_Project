// Client-side search over a fruit list fetched from the API.
// The ?inject= modes exist only to seed the labeled trace corpus (Phase 4a);
// with no query param this behaves as the normal app.

const INJECT = new URLSearchParams(window.location.search).get('inject');

const searchInput = document.getElementById('search');
const resultsList = document.getElementById('results');
const emptyState = document.getElementById('empty-state');
const loadError = document.getElementById('load-error');

let allFruits = [];

function matchesFor(query) {
  const q = query.trim().toLowerCase();
  if (!q) return allFruits;
  if (INJECT === 'real_bug') {
    // Injected bug: inverted match — returns the fruits that do NOT match.
    return allFruits.filter((name) => !name.toLowerCase().includes(q));
  }
  return allFruits.filter((name) => name.toLowerCase().includes(q));
}

function paint(query) {
  const matches = matchesFor(query);
  resultsList.replaceChildren();
  for (const name of matches) {
    const li = document.createElement('li');
    li.className = 'result-item';
    li.setAttribute('data-testid', 'result-item');
    li.textContent = name;
    resultsList.appendChild(li);
  }
  emptyState.hidden = matches.length > 0;
}

function render(query) {
  if (INJECT === 'flaky' && query.trim()) {
    // Injected bug: the search result lands ~3s late, so an early assertion
    // sees stale UI.
    window.setTimeout(() => paint(query), 3000);
    return;
  }
  paint(query);
}

async function load() {
  try {
    const response = await fetch('/api/fruits.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    allFruits = await response.json();
  } catch (error) {
    loadError.hidden = false;
    loadError.textContent = `Failed to load fruits: ${error.message}`;
    return;
  }
  render('');
  searchInput.addEventListener('input', (event) => render(event.target.value));
}

load();
