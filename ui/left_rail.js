(() => {
  const routeCopy = {
    garage: {
      eyebrow: 'Workbench · Agent Garage',
      title: 'Draft a coordinator agent',
      subtitle: 'Saved drafts come from the local backend. Assistant proposal generation lands next.',
    },
    replays: {
      eyebrow: 'Workbench · Film Room',
      title: 'Watch film with the assistant',
      subtitle: 'Open a replay, inspect evidence, then send a structured request event for the next phase.',
    },
    reports: {
      eyebrow: 'Workbench · Reports',
      title: 'Compare fixed-seed outcomes',
      subtitle: 'Use reports to inspect repeatable changes before rematching.',
    },
    arena: {
      eyebrow: 'Workbench · Arena',
      title: 'Run gauntlets from saved drafts',
      subtitle: 'Arena is the retention loop: build, run, watch film, adjust, rerun.',
    },
  };

  const $ = id => document.getElementById(id);
  const escapeHtml = raw => String(raw ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const label = raw => String(raw || '').replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase());

  async function fetchJson(path) {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`${path} ${response.status}`);
    return response.json();
  }

  async function fetchApi(path) {
    return fetchJson(path);
  }

  function dispatch(detail) {
    window.dispatchEvent(new CustomEvent('coachbench:assistant:request', { detail }));
  }

  function relativeTime(raw) {
    if (!raw) return 'recent';
    const then = new Date(raw).getTime();
    if (!Number.isFinite(then)) return 'recent';
    const diff = Math.max(0, Date.now() - then);
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  }

  function identityLabel(left, right, leftTech, rightTech) {
    const offense = left || leftTech || 'Offense';
    const defense = right || rightTech || 'Defense';
    return `${offense} ⇌ ${defense}`;
  }

  function renderEmpty(id, statusId, copy) {
    const target = $(id);
    if (target) target.innerHTML = `<p class="offline-state">${escapeHtml(copy)}</p>`;
    const status = $(statusId);
    if (status) status.textContent = 'offline';
  }

  function renderIdentities(payload) {
    const identities = payload?.identities || [];
    const target = $('railIdentities');
    const status = $('railIdentityStatus');
    if (status) status.textContent = identities.length ? String(identities.length) : '0';
    if (!target) return;
    target.innerHTML = identities.length
      ? identities.map(identity => `<button class="rail-card rail-card--button" type="button" data-identity-id="${escapeHtml(identity.id)}">
          <strong>${escapeHtml(identity.display_name)}</strong>
          <span>${escapeHtml(identity.coordinator_style)}</span>
        </button>`).join('')
      : '<p class="offline-state">Backend offline. Opponents unavailable.</p>';
    target.querySelectorAll('[data-identity-id]').forEach(button => {
      button.onclick = () => {
        target.querySelectorAll('[data-identity-id]').forEach(row => row.classList.toggle('active', row === button));
        window.CBState?.set({ selectedIdentityId: button.dataset.identityId });
        dispatch({ type: 'identity_selected', identity_id: button.dataset.identityId });
      };
    });
  }

  async function loadSessions() {
    const [arena, runs] = await Promise.allSettled([
      fetchApi('/v1/arena/sessions?limit=20'),
      fetchApi('/v1/sessions?limit=20'),
    ]);
    const rows = [
      ...((arena.status === 'fulfilled' && arena.value.sessions) || []),
      ...((runs.status === 'fulfilled' && runs.value.sessions) || []),
    ];
    const deduped = new Map();
    rows.forEach(row => deduped.set(row.id, row));
    return [...deduped.values()]
      .sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))
      .slice(0, 20);
  }

  async function loadShowcaseCards() {
    const manifest = await fetchJson('showcase_manifest.json').catch(() => ({ replays: [] }));
    return (manifest.replays || []).slice(0, 4).map(item => ({
      id: `seed-${item.seed}`,
      label: identityLabel(item.offense_label, item.defense_label, item.technical_label?.offense, item.technical_label?.defense),
      meta: `Seed ${item.seed} · ${label(item.summary?.result)} · ${item.summary?.plays ?? '-'} plays`,
    }));
  }

  function renderSessions(rows) {
    const target = $('railSessions');
    const status = $('railSessionStatus');
    if (status) status.textContent = rows.length ? String(rows.length) : '0';
    if (!target) return;
    target.innerHTML = rows.length
      ? rows.map(row => `<button class="rail-card rail-card--button" type="button" data-open-replay="${escapeHtml(row.id)}">
          <strong>${escapeHtml(identityLabel(row.offense_label, row.defense_label, row.offense_technical_label, row.defense_technical_label))}</strong>
          <span>${escapeHtml(relativeTime(row.created_at))}${row.seed ? ` · seed ${escapeHtml(row.seed)}` : ''}</span>
        </button>`).join('')
      : '<p class="offline-state">Backend offline. Past runs unavailable.</p>';
  }

  function renderWatchFilmCards(cards) {
    const target = $('watchFilmCards');
    if (!target) return;
    target.innerHTML = cards.map(card => `<article class="watch-film-card">
      <div class="watch-film-icon" aria-hidden="true"></div>
      <div>
        <strong>${escapeHtml(card.label)}</strong>
        <span>${escapeHtml(card.meta)}</span>
      </div>
      <button class="btn" type="button" data-open-replay="${escapeHtml(card.id)}">Open</button>
    </article>`).join('');
  }

  async function refreshDraftStatus() {
    const status = $('draftSourceStatus');
    if (!status) return;
    try {
      const payload = await fetchApi('/v1/drafts');
      const drafts = payload.drafts || [];
      window.CBState?.set({ garageDrafts: drafts, garageDraftSource: 'backend' });
      status.innerHTML = `<span class="validation-badge is-ok">Backend source</span><span>${escapeHtml(drafts.length)} saved drafts available.</span>`;
    } catch {
      window.CBState?.set({ garageDrafts: [], garageDraftSource: 'offline' });
      status.innerHTML = '<span class="validation-badge is-warn">Offline mode</span><span>Backend offline. Current tab cache only.</span>';
    }
  }

  function bindReplayButtons(root = document) {
    root.querySelectorAll('[data-open-replay]').forEach(button => {
      button.onclick = () => window.CBRouter?.go('replay-detail', { id: button.dataset.openReplay });
    });
  }

  function bindPrompts() {
    document.querySelectorAll('[data-canonical-prompt]').forEach(button => {
      button.onclick = () => dispatch({ type: 'canonical_prompt', text: button.dataset.canonicalPrompt });
    });
    const form = $('assistantPromptForm');
    if (form) form.onsubmit = event => event.preventDefault();
  }

  function bindDrawer() {
    const close = () => window.CBRouter?.go('replays');
    $('closeRightDrawer')?.addEventListener('click', close);
    $('rightDrawerScrim')?.addEventListener('click', close);
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !$('rightDrawer')?.hidden) close();
    });
  }

  function updateRouteCopy(route) {
    const copy = routeCopy[route.name === 'replay-detail' ? 'replays' : route.name] || routeCopy.replays;
    const eyebrow = $('assistantEyebrow');
    const title = $('assistantTitle');
    const subtitle = $('assistantSubtitle');
    if (eyebrow) eyebrow.textContent = copy.eyebrow;
    if (title) title.textContent = copy.title;
    if (subtitle) subtitle.textContent = copy.subtitle;
    if (route.name === 'garage') refreshDraftStatus();
  }

  async function refresh() {
    await fetchApi('/v1/identities')
      .then(renderIdentities)
      .catch(() => renderEmpty('railIdentities', 'railIdentityStatus', 'Backend offline. Opponents unavailable.'));

    const sessions = await loadSessions().catch(() => []);
    renderSessions(sessions);
    const cards = sessions.length
      ? sessions.slice(0, 4).map(row => ({
          id: row.id,
          label: identityLabel(row.offense_label, row.defense_label, row.offense_technical_label, row.defense_technical_label),
          meta: `${relativeTime(row.created_at)}${row.seed ? ` · seed ${row.seed}` : ''}`,
        }))
      : await loadShowcaseCards();
    renderWatchFilmCards(cards);
    bindReplayButtons();
    refreshDraftStatus();
  }

  function init() {
    if (!$('appRoot')?.dataset.shellRoot) return;
    bindPrompts();
    bindDrawer();
    refresh().catch(() => {
      renderEmpty('railIdentities', 'railIdentityStatus', 'Backend offline. Opponents unavailable.');
      renderEmpty('railSessions', 'railSessionStatus', 'Backend offline. Past runs unavailable.');
    });
    window.CBRouter?.subscribe(updateRouteCopy);
    if (window.CBRouter) updateRouteCopy(window.CBRouter.current());
  }

  window.CBLeftRail = { refresh, bindReplayButtons, updateRouteCopy };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
