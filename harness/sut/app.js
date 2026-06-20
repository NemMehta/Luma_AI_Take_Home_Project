// Minimal client-side search filter — the one interactive flow under test.
const ALL_FRUITS = [
  'Apple',
  'Apricot',
  'Banana',
  'Cherry',
  'Grape',
  'Orange',
  'Peach',
  'Pear',
];

const searchInput = document.getElementById('search');
const resultsList = document.getElementById('results');
const emptyState = document.getElementById('empty-state');

function render(query) {
  const q = query.trim().toLowerCase();
  const matches = q
    ? ALL_FRUITS.filter((name) => name.toLowerCase().includes(q))
    : ALL_FRUITS;

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

searchInput.addEventListener('input', (event) => render(event.target.value));
render('');
