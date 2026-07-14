/* =============================================================================
   AI Recipe Agent — Frontend Application
   Handles: Chat, Recipe Dashboard, Ingredient Manager, Search, Preferences
============================================================================= */

'use strict';

// ---------------------------------------------------------------------------
// STATE
// ---------------------------------------------------------------------------
const State = {
  sessionId:     localStorage.getItem('recipe_agent_session') || generateId(),
  ingredients:   JSON.parse(localStorage.getItem('recipe_agent_ingredients') || '[]'),
  dietaryPrefs:  JSON.parse(localStorage.getItem('recipe_agent_diets') || '[]'),
  allergies:     JSON.parse(localStorage.getItem('recipe_agent_allergies') || '[]'),
  isLoading:     false,
  currentModal:  null,
  searchTimeout: null,
};

// Persist session ID
localStorage.setItem('recipe_agent_session', State.sessionId);

// ---------------------------------------------------------------------------
// CONSTANTS
// ---------------------------------------------------------------------------
const COMMON_INGREDIENTS = [
  'Chicken', 'Eggs', 'Garlic', 'Onion', 'Tomatoes', 'Pasta', 'Rice',
  'Butter', 'Olive Oil', 'Lemon', 'Potatoes', 'Carrots', 'Bell Pepper',
  'Mushrooms', 'Cheese', 'Milk', 'Flour', 'Sugar', 'Salt', 'Black Pepper',
];

const DIET_OPTIONS = [
  'Vegetarian', 'Vegan', 'Gluten-Free', 'Dairy-Free', 'Keto',
  'Paleo', 'Low-Carb', 'Low-Sodium', 'Nut-Free', 'Halal', 'Kosher',
];

const ALLERGY_OPTIONS = [
  'Milk', 'Eggs', 'Fish', 'Shellfish', 'Tree Nuts',
  'Peanuts', 'Wheat', 'Soy', 'Sesame',
];

const CUISINE_ICONS = {
  'Italian': '🍝', 'Indian': '🍛', 'Mexican': '🌮', 'Asian': '🥢',
  'American': '🍔', 'Mediterranean': '🫒', 'Middle Eastern': '🥙',
  'African': '🌍', 'French': '🥐',
};

// ---------------------------------------------------------------------------
// UTILS
// ---------------------------------------------------------------------------
function generateId() {
  return 'sess_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function formatTime(isoStr) {
  return new Date(isoStr || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

function showToast(message, type = 'success') {
  const toastEl = document.getElementById('liveToast');
  const body = document.getElementById('toastBody');
  body.textContent = message;
  toastEl.className = `toast align-items-center border-0 text-bg-${type}`;
  bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 3000 }).show();
}

function persistIngredients() {
  localStorage.setItem('recipe_agent_ingredients', JSON.stringify(State.ingredients));
}
function persistPrefs() {
  localStorage.setItem('recipe_agent_diets',     JSON.stringify(State.dietaryPrefs));
  localStorage.setItem('recipe_agent_allergies', JSON.stringify(State.allergies));
}

// ---------------------------------------------------------------------------
// TAB NAVIGATION
// ---------------------------------------------------------------------------
function switchTab(tab) {
  const panels = { chat: 'tabChat', dashboard: 'tabDashboard', ingredients: 'tabIngredients', search: 'tabSearch', prefs: 'tabPrefs' };
  const navIds  = { chat: 'navChat', dashboard: 'navDashboard', ingredients: 'navIngredients', search: 'navSearch', prefs: 'navPrefs' };

  Object.values(panels).forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('active');
  });
  Object.values(navIds).forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('active');
  });

  const panelEl = document.getElementById(panels[tab]);
  const navEl   = document.getElementById(navIds[tab]);
  if (panelEl) panelEl.classList.add('active');
  if (navEl)   navEl.classList.add('active');

  // Lazy-load tab data
  if (tab === 'dashboard')   loadDashboard();
  if (tab === 'ingredients') renderIngredients();
  if (tab === 'prefs')       renderPreferences();

  // Close mobile nav
  const navCollapse = document.getElementById('navContent');
  if (navCollapse && navCollapse.classList.contains('show')) {
    bootstrap.Collapse.getOrCreateInstance(navCollapse).hide();
  }
}

// ---------------------------------------------------------------------------
// THEME TOGGLE
// ---------------------------------------------------------------------------
function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') === 'dark';
  html.setAttribute('data-theme', isDark ? 'light' : 'dark');
  document.getElementById('themeIcon').className = isDark ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';
  localStorage.setItem('recipe_agent_theme', isDark ? 'light' : 'dark');
}

function applyStoredTheme() {
  const theme = localStorage.getItem('recipe_agent_theme') || 'light';
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('themeIcon').className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
}

// ---------------------------------------------------------------------------
// CHAT — Core
// ---------------------------------------------------------------------------
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const text  = input.value.trim();
  if (!text || State.isLoading) return;

  input.value = '';
  input.style.height = 'auto';
  hideWelcomeCard();
  appendMessage('user', text);
  setLoading(true);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id:  State.sessionId,
        message:     text,
        ingredients: State.ingredients,
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Server error');

    appendMessage('ai', data.reply, data.timestamp);
    updateRetrievedRecipes(data.retrieved_recipes || []);

    // Sync preferences detected from message
    if (data.dietary_prefs?.length) {
      State.dietaryPrefs = data.dietary_prefs;
      persistPrefs();
    }

  } catch (err) {
    appendMessage('ai', `⚠️ **Error:** ${err.message}. Please try again.`);
  } finally {
    setLoading(false);
  }
}

function sendStarter(text) {
  document.getElementById('chatInput').value = text;
  sendMessage();
}

function handleInputKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

// ---------------------------------------------------------------------------
// CHAT — Quick Actions
// ---------------------------------------------------------------------------
async function quickAction(action) {
  hideWelcomeCard();
  setLoading(true);

  const actionLabels = {
    suggest_with_ingredients: '🔍 Finding recipes with your pantry...',
    random_recipe:            '🎲 Picking a surprise recipe for you...',
    cooking_tip:              '💡 Fetching a pro tip...',
    substitutions:            '🔄 Loading substitution guide...',
    meal_plan:                '📅 Building your meal plan...',
  };

  appendMessage('user', actionLabels[action] || action, null, true);

  try {
    const res = await fetch('/api/quick-action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: State.sessionId, action }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Server error');

    appendMessage('ai', data.reply, data.timestamp);

  } catch (err) {
    appendMessage('ai', `⚠️ **Error:** ${err.message}`);
  } finally {
    setLoading(false);
  }
}

async function clearChat() {
  try {
    await fetch('/api/session/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: State.sessionId }),
    });
  } catch (_) {}

  const messages = document.getElementById('chatMessages');
  messages.innerHTML = '';
  showWelcomeCard();
  document.getElementById('retrievedRecipes').innerHTML = '<p class="empty-text">Recipes will appear here after you chat.</p>';
  showToast('Chat history cleared', 'secondary');
}

// ---------------------------------------------------------------------------
// CHAT — DOM Helpers
// ---------------------------------------------------------------------------
function appendMessage(role, content, timestamp = null, isAction = false) {
  const welcomeCard = document.getElementById('welcomeCard');
  if (welcomeCard) welcomeCard.remove();

  const messages = document.getElementById('chatMessages');
  const wrapper  = document.createElement('div');
  wrapper.className = `chat-bubble-wrapper ${role}`;

  const avatar = document.createElement('div');
  avatar.className = `bubble-avatar ${role === 'user' ? 'user' : 'ai'}`;
  avatar.innerHTML = role === 'user' ? '<i class="bi bi-person-fill"></i>' : '<i class="bi bi-fire"></i>';

  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role === 'user' ? 'user' : 'ai'}`;

  if (role === 'ai') {
    bubble.innerHTML = marked.parse(content || '');
  } else {
    if (isAction) {
      bubble.style.fontStyle = 'italic';
      bubble.style.opacity = '0.85';
    }
    bubble.textContent = content;
  }

  const timeEl = document.createElement('div');
  timeEl.className = 'bubble-time';
  timeEl.textContent = formatTime(timestamp);

  const inner = document.createElement('div');
  inner.style.maxWidth = '72%';
  inner.appendChild(bubble);
  inner.appendChild(timeEl);

  if (role === 'user') {
    wrapper.appendChild(inner);
    wrapper.appendChild(avatar);
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(inner);
  }

  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

function hideWelcomeCard() {
  const card = document.getElementById('welcomeCard');
  if (card) card.style.display = 'none';
}
function showWelcomeCard() {
  const messages = document.getElementById('chatMessages');
  const card = document.createElement('div');
  card.id = 'welcomeCard';
  card.className = 'welcome-card';
  card.innerHTML = document.querySelector('[data-welcome-template]')?.innerHTML || '';
  messages.appendChild(card);
}

function setLoading(state) {
  State.isLoading = state;
  const indicator = document.getElementById('typingIndicator');
  const sendBtn   = document.getElementById('sendBtn');

  if (state) {
    indicator.classList.remove('d-none');
    sendBtn.disabled = true;
    document.getElementById('chatMessages').scrollTop = 99999;
  } else {
    indicator.classList.add('d-none');
    sendBtn.disabled = false;
  }
}

function updateRetrievedRecipes(recipes) {
  const container = document.getElementById('retrievedRecipes');
  if (!recipes?.length) {
    container.innerHTML = '<p class="empty-text">No closely matching recipes found in the database.</p>';
    return;
  }
  container.innerHTML = recipes.slice(0, 4).map((r, i) => `
    <div class="retrieved-item" onclick="openRecipeModal('${r.id}')"
         style="animation-delay: ${i * 0.07}s">
      <div class="retrieved-item-name">${getCuisineIcon(r.cuisine)} ${r.name}</div>
      <div class="retrieved-item-meta">${r.cuisine} · ${r.difficulty}</div>
      <div class="retrieved-item-score">Relevance: ${(r.score * 100).toFixed(0)}%</div>
    </div>
  `).join('');
}

// ---------------------------------------------------------------------------
// INGREDIENT BAR (Chat Tab)
// ---------------------------------------------------------------------------
function toggleIngredientBar() {
  const bar = document.getElementById('inlineIngredientAdd');
  const isHidden = bar.classList.contains('d-none');
  bar.classList.toggle('d-none', !isHidden);
  if (isHidden) {
    setTimeout(() => document.getElementById('inlineIngredientInput').focus(), 50);
  }
}

function addInlineIngredient() {
  const input = document.getElementById('inlineIngredientInput');
  const val = input.value.trim();
  if (!val) return;

  if (!State.ingredients.includes(val)) {
    State.ingredients.push(val);
    persistIngredients();
  }

  input.value = '';
  renderChatIngredientBar();
  updatePantryCount();
  document.getElementById('inlineIngredientAdd').classList.add('d-none');
}

function removeInlineIngredient(ingredient) {
  State.ingredients = State.ingredients.filter(i => i !== ingredient);
  persistIngredients();
  renderChatIngredientBar();
  updatePantryCount();
}

function renderChatIngredientBar() {
  const container = document.getElementById('quickIngredientTags');
  container.innerHTML = State.ingredients.map(ing => `
    <div class="quick-ingredient-tag">
      ${ing}
      <button onclick="removeInlineIngredient('${ing}')" title="Remove"><i class="bi bi-x-lg"></i></button>
    </div>
  `).join('');

  // Update sidebar
  const sidebar = document.getElementById('sidebarIngredients');
  if (!State.ingredients.length) {
    sidebar.innerHTML = `<p class="empty-text">No ingredients added yet. <a href="#" onclick="switchTab('ingredients'); return false;">Add some →</a></p>`;
  } else {
    sidebar.innerHTML = State.ingredients.map(i => `<span class="sidebar-ingredient-tag">${i}</span>`).join('');
  }
}

function updatePantryCount() {
  const count = State.ingredients.length;
  document.getElementById('pantryCount').textContent = count;
  const big = document.getElementById('pantryCountBig');
  if (big) big.textContent = count;
}

// ---------------------------------------------------------------------------
// INGREDIENT MANAGER (Pantry Tab)
// ---------------------------------------------------------------------------
function addIngredient() {
  const input = document.getElementById('ingredientInput');
  const val   = input.value.trim();
  if (!val) return;

  const items = val.split(',').map(s => s.trim()).filter(Boolean);
  items.forEach(item => {
    if (item && !State.ingredients.includes(item)) State.ingredients.push(item);
  });

  persistIngredients();
  input.value = '';
  renderIngredients();
  renderChatIngredientBar();
  updatePantryCount();
  syncIngredientsWithServer();
}

function removeIngredient(ingredient) {
  State.ingredients = State.ingredients.filter(i => i !== ingredient);
  persistIngredients();
  renderIngredients();
  renderChatIngredientBar();
  updatePantryCount();
}

function clearIngredients() {
  if (!State.ingredients.length) return;
  if (!confirm('Clear all pantry ingredients?')) return;
  State.ingredients = [];
  persistIngredients();
  renderIngredients();
  renderChatIngredientBar();
  updatePantryCount();
  showToast('Pantry cleared', 'warning');
}

function renderIngredients() {
  const list = document.getElementById('ingredientsList');
  const actions = document.getElementById('pantryActions');
  const countEl = document.getElementById('pantryCountBig');

  if (countEl) countEl.textContent = State.ingredients.length;

  if (!State.ingredients.length) {
    list.innerHTML = `
      <div class="empty-pantry">
        <i class="bi bi-basket display-4 d-block mb-3 text-muted"></i>
        <p class="text-muted">Your pantry is empty.<br>Add ingredients to get personalized recipe suggestions!</p>
      </div>`;
    if (actions) actions.style.setProperty('display', 'none', 'important');
    return;
  }

  list.innerHTML = State.ingredients.map((ing, i) => `
    <div class="ingredient-chip" style="animation-delay: ${i * 0.04}s">
      <i class="bi bi-check-circle-fill" style="font-size:13px"></i>
      ${ing}
      <button class="ingredient-chip-del" onclick="removeIngredient('${ing}')" title="Remove">
        <i class="bi bi-x-lg"></i>
      </button>
    </div>
  `).join('');

  if (actions) actions.style.removeProperty('display');
}

function renderCommonIngredients() {
  const container = document.getElementById('commonTags');
  container.innerHTML = COMMON_INGREDIENTS.map(i => `
    <span class="common-tag" onclick="addCommonIngredient('${i}')">${i}</span>
  `).join('');
}

function addCommonIngredient(ing) {
  if (!State.ingredients.includes(ing)) {
    State.ingredients.push(ing);
    persistIngredients();
    renderIngredients();
    renderChatIngredientBar();
    updatePantryCount();
  }
}

async function syncIngredientsWithServer() {
  try {
    await fetch('/api/ingredients', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: State.sessionId, ingredients: State.ingredients }),
    });
  } catch (_) {}
}

// ---------------------------------------------------------------------------
// RECIPE DASHBOARD
// ---------------------------------------------------------------------------
async function loadDashboard() {
  const cuisine    = document.getElementById('filterCuisine')?.value || '';
  const diet       = document.getElementById('filterDiet')?.value || '';
  const difficulty = document.getElementById('filterDifficulty')?.value || '';
  const grid       = document.getElementById('recipeGrid');
  const countBadge = document.getElementById('dashboardCount');

  if (!grid) return;

  // Show skeleton
  grid.innerHTML = Array(6).fill('<div class="skeleton-card"></div>').join('');

  try {
    const params = new URLSearchParams({ cuisine, diet, difficulty });
    const res    = await fetch(`/api/recipes/search?${params}`);
    const data   = await res.json();
    const recipes = data.recipes || [];

    countBadge.textContent = `${recipes.length} recipe${recipes.length !== 1 ? 's' : ''}`;

    if (!recipes.length) {
      grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:60px 0; color: var(--text-muted)">
        <i class="bi bi-search display-4 d-block mb-3"></i>
        <p>No recipes match the selected filters.</p>
      </div>`;
      return;
    }

    grid.innerHTML = recipes.map((r, i) => buildRecipeCard(r, i)).join('');

  } catch (err) {
    grid.innerHTML = `<div style="grid-column:1/-1; color:var(--red); padding:20px">Error loading recipes: ${err.message}</div>`;
  }
}

function buildRecipeCard(r, animIndex = 0) {
  const icon = getCuisineIcon(r.cuisine);
  const dietTagsHtml = (r.diet_tags || []).map(t =>
    `<span class="diet-tag">${t}</span>`
  ).join('');

  return `
    <div class="recipe-card" onclick="openRecipeModal('${r.id}')"
         style="animation-delay: ${animIndex * 0.06}s">
      <div class="recipe-card-header">
        <div class="recipe-cuisine-badge">${icon} ${r.cuisine}</div>
        <div class="recipe-card-name">${r.name}</div>
        <div class="recipe-card-desc">${r.description || ''}</div>
      </div>
      ${dietTagsHtml ? `<div class="diet-tags-row">${dietTagsHtml}</div>` : ''}
      <div class="recipe-card-footer">
        <span class="recipe-stat"><i class="bi bi-clock"></i> ${r.prep_time}</span>
        <span class="recipe-stat"><i class="bi bi-fire"></i> ${r.cook_time}</span>
        <span class="recipe-stat"><i class="bi bi-people"></i> ${r.servings}</span>
        <span class="difficulty-badge ${r.difficulty}">${r.difficulty}</span>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// RECIPE SEARCH
// ---------------------------------------------------------------------------
const debounceSearch = debounce(doSearch, 400);

async function doSearch() {
  const query     = document.getElementById('searchInput')?.value.trim() || '';
  const clearBtn  = document.getElementById('searchClearBtn');
  const results   = document.getElementById('searchResults');

  if (clearBtn) clearBtn.style.display = query ? 'block' : 'none';

  if (!query) {
    results.innerHTML = `<p class="search-hint text-center text-muted py-5">
      <i class="bi bi-search display-4 d-block mb-3"></i>
      Start typing to search recipes...
    </p>`;
    return;
  }

  results.innerHTML = Array(4).fill('<div class="skeleton-card"></div>').join('');

  try {
    const res  = await fetch(`/api/recipes/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    const list = data.recipes || [];

    if (!list.length) {
      results.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:60px 0; color:var(--text-muted)">
        <i class="bi bi-emoji-frown display-4 d-block mb-3"></i>
        <p>No recipes found for "<strong>${query}</strong>"</p>
        <button class="btn-primary-action mt-3" onclick="askChefAboutSearch('${query}')">
          <i class="bi bi-chat-dots"></i> Ask Chef Aria Instead
        </button>
      </div>`;
      return;
    }

    results.innerHTML = list.map((r, i) => buildRecipeCard(r, i)).join('');

  } catch (err) {
    results.innerHTML = `<div style="color:var(--red)">Search error: ${err.message}</div>`;
  }
}

function clearSearch() {
  document.getElementById('searchInput').value = '';
  document.getElementById('searchClearBtn').style.display = 'none';
  document.getElementById('searchResults').innerHTML = `<p class="search-hint text-center text-muted py-5">
    <i class="bi bi-search display-4 d-block mb-3"></i>
    Start typing to search recipes...
  </p>`;
}

function askChefAboutSearch(query) {
  switchTab('chat');
  setTimeout(() => {
    document.getElementById('chatInput').value = `I'm looking for recipes for "${query}". Any suggestions?`;
    sendMessage();
  }, 200);
}

// ---------------------------------------------------------------------------
// RECIPE MODAL
// ---------------------------------------------------------------------------
async function openRecipeModal(recipeId) {
  try {
    const res    = await fetch(`/api/recipes/${recipeId}`);
    const recipe = await res.json();
    if (!res.ok) throw new Error(recipe.error || 'Not found');

    State.currentModal = recipe;
    populateModal(recipe);
    bootstrap.Modal.getOrCreateInstance(document.getElementById('recipeModal')).show();

  } catch (err) {
    showToast(`Could not load recipe: ${err.message}`, 'danger');
  }
}

function populateModal(r) {
  document.getElementById('modalRecipeName').textContent = r.name;
  document.getElementById('modalDescription').textContent = r.description || '';

  document.getElementById('modalMeta').innerHTML = [
    `<span class="modal-meta-badge">${getCuisineIcon(r.cuisine)} ${r.cuisine}</span>`,
    `<span class="modal-meta-badge"><i class="bi bi-clock"></i> Prep: ${r.prep_time}</span>`,
    `<span class="modal-meta-badge"><i class="bi bi-fire"></i> Cook: ${r.cook_time}</span>`,
    `<span class="modal-meta-badge"><i class="bi bi-people"></i> Serves ${r.servings}</span>`,
    `<span class="modal-meta-badge">${r.difficulty}</span>`,
  ].join('');

  document.getElementById('modalStats').innerHTML = `
    <div class="stat-item"><div class="stat-label">Prep Time</div><div class="stat-value">${r.prep_time}</div></div>
    <div class="stat-item"><div class="stat-label">Cook Time</div><div class="stat-value">${r.cook_time}</div></div>
    <div class="stat-item"><div class="stat-label">Servings</div><div class="stat-value">${r.servings}</div></div>
    <div class="stat-item"><div class="stat-label">Difficulty</div><div class="stat-value">${r.difficulty}</div></div>
  `;

  document.getElementById('modalIngredients').innerHTML =
    (r.ingredients || []).map(i => `<li>${i}</li>`).join('');

  document.getElementById('modalInstructions').innerHTML =
    (r.instructions || []).map(step => `<li>${step}</li>`).join('');

  document.getElementById('modalTips').innerHTML =
    (r.tips || []).map(tip => `<li>${tip}</li>`).join('');

  const allergenSection = document.getElementById('modalAllergenSection');
  if (r.allergens?.length) {
    document.getElementById('modalAllergens').innerHTML =
      r.allergens.map(a => `<span class="pref-tag" style="background:rgba(239,68,68,0.08);border-color:var(--red);color:var(--red)">${a}</span>`).join(' ');
    allergenSection.style.display = 'block';
  } else {
    allergenSection.style.display = 'none';
  }
}

function cookNowFromModal() {
  const recipe = State.currentModal;
  if (!recipe) return;
  bootstrap.Modal.getOrCreateInstance(document.getElementById('recipeModal')).hide();
  switchTab('chat');
  setTimeout(() => {
    document.getElementById('chatInput').value =
      `Please guide me step-by-step through making ${recipe.name}. I want detailed instructions, tips, and any helpful tricks!`;
    sendMessage();
  }, 300);
}

// ---------------------------------------------------------------------------
// PREFERENCES
// ---------------------------------------------------------------------------
function renderPreferences() {
  // Diet tags
  const dietContainer = document.getElementById('dietTags');
  if (dietContainer) {
    dietContainer.innerHTML = DIET_OPTIONS.map(opt => `
      <span class="pref-tag ${State.dietaryPrefs.includes(opt) ? 'selected' : ''}"
            onclick="togglePref('diet', '${opt}', this)">${opt}</span>
    `).join('');
  }

  // Allergy tags
  const allergyContainer = document.getElementById('allergyTags');
  if (allergyContainer) {
    allergyContainer.innerHTML = ALLERGY_OPTIONS.map(opt => `
      <span class="pref-tag ${State.allergies.includes(opt) ? 'selected-allergy' : ''}"
            onclick="togglePref('allergy', '${opt}', this)">${opt}</span>
    `).join('');
  }
}

function togglePref(type, value, el) {
  if (type === 'diet') {
    const idx = State.dietaryPrefs.indexOf(value);
    if (idx > -1) { State.dietaryPrefs.splice(idx, 1); el.classList.remove('selected'); }
    else          { State.dietaryPrefs.push(value);    el.classList.add('selected'); }
  } else {
    const idx = State.allergies.indexOf(value);
    if (idx > -1) { State.allergies.splice(idx, 1); el.classList.remove('selected-allergy'); }
    else          { State.allergies.push(value);    el.classList.add('selected-allergy'); }
  }
}

async function savePreferences() {
  persistPrefs();
  try {
    await fetch('/api/session/preferences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id:   State.sessionId,
        dietary_prefs: State.dietaryPrefs,
        allergies:    State.allergies,
      }),
    });
  } catch (_) {}

  const status = document.getElementById('prefSaveStatus');
  status.textContent = '✓ Preferences saved!';
  status.classList.add('visible');
  setTimeout(() => status.classList.remove('visible'), 3000);
  showToast('Preferences saved! Chef Aria will personalise your next suggestions.', 'success');
}

// ---------------------------------------------------------------------------
// UTILITIES
// ---------------------------------------------------------------------------
function getCuisineIcon(cuisine = '') {
  for (const [key, icon] of Object.entries(CUISINE_ICONS)) {
    if (cuisine.toLowerCase().includes(key.toLowerCase())) return icon;
  }
  return '🍽️';
}

// ---------------------------------------------------------------------------
// INIT
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  applyStoredTheme();
  renderChatIngredientBar();
  updatePantryCount();
  renderCommonIngredients();

  // Configure marked.js
  marked.setOptions({
    breaks: true,
    gfm:    true,
  });

  // Load initial dashboard quietly
  loadDashboard();
});
