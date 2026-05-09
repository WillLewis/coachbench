(() => {
  const routeCopy = {
    garage: {
      eyebrow: 'Workbench · Agent Garage',
      title: 'Draft a coordinator agent',
      subtitle: 'Describe the coordinator you want. The Assistant proposes structured changes you can accept, reject, or edit.',
    },
    replays: {
      eyebrow: 'Workbench · Film Room',
      title: 'Watch film with the assistant',
      subtitle: 'Open a replay, inspect graph evidence, then ask for a grounded adjustment.',
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
      result: item.summary?.result,
    }));
  }

  function renderSessions(rows) {
    const target = $('railSessions');
    const status = $('railSessionStatus');
    if (status) status.textContent = rows.length ? String(rows.length) : '0';
    if (!target) return;
    target.innerHTML = rows.length
      ? rows.map(row => {
          const result = row.result || row.terminal_result || row.score?.result;
          const dot = window.CBChips?.seedDotClass?.(result) || 'seed-dot';
          return `<button class="rail-card rail-card--button" type="button" data-open-replay="${escapeHtml(row.id)}">
            <span class="rail-card__row">
              <span class="${dot} rail-card__dot"></span>
              <strong class="rail-card__title">${escapeHtml(identityLabel(row.offense_label, row.defense_label, row.offense_technical_label, row.defense_technical_label))}</strong>
            </span>
            <span class="rail-card__meta">${escapeHtml(relativeTime(row.created_at))}${row.seed ? ` · seed ${escapeHtml(row.seed)}` : ''}</span>
          </button>`;
        }).join('')
      : '<p class="offline-state">Backend offline. Past runs unavailable.</p>';
  }

  function renderWatchFilmCards(cards) {
    const target = $('watchFilmCards');
    const status = $('railWatchFilmStatus');
    if (status) status.textContent = cards.length ? String(cards.length) : '0';
    if (!target) return;
    const filmIcon = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="2.5" y="3.5" width="11" height="9" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M5 3.5v9M11 3.5v9M2.5 6h11M2.5 10h11" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>';
    target.innerHTML = cards.map(card => {
      const dot = window.CBChips?.seedDotClass?.(card.result) || 'seed-dot';
      return `<button class="rail-card rail-card--button" type="button" data-open-replay="${escapeHtml(card.id)}">
        <span class="rail-card__row">
          <span class="${dot} rail-card__dot"></span>
          <span class="rail-card__icon">${filmIcon}</span>
          <strong class="rail-card__title">${escapeHtml(card.label)}</strong>
        </span>
        <span class="rail-card__meta">${escapeHtml(card.meta)}</span>
      </button>`;
    }).join('');
  }

  async function refreshDraftStatus() {
    const status = $('draftSourceStatus');
    if (!status) return;
    try {
      const payload = await fetchApi('/v1/drafts');
      const drafts = payload.drafts || [];
      const state = window.CBState?.get?.() || {};
      const activeDraftId = drafts.some(draft => draft.id === state.activeDraftId) ? state.activeDraftId : null;
      window.CBState?.set({ garageDrafts: drafts, garageDraftSource: 'backend', activeDraftId });
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
    const isWorkbenchRoute = ['garage', 'replays', 'replay-detail'].includes(route.name);
    if (eyebrow) eyebrow.textContent = copy.eyebrow.toUpperCase();
    if (title) title.textContent = copy.title;
    if (subtitle) {
      subtitle.textContent = copy.subtitle;
      subtitle.hidden = isWorkbenchRoute;
    }
    const segmented = $('routeSegmentedToggle');
    if (segmented) segmented.hidden = !isWorkbenchRoute;
    $('newDraftButton')?.toggleAttribute('hidden', route.name !== 'garage');
    $('saveDraftButton')?.toggleAttribute('hidden', route.name !== 'garage');
    renderRouteSystemMessage(route);
    renderFilmRoomEmptyState(route);
    syncReplayChrome();
    if (route.name === 'garage') refreshDraftStatus();
  }

  function renderRouteSystemMessage(route) {
    const copy = $('assistantSystemCopy');
    if (!copy) return;
    if (route.name === 'replays' || route.name === 'replay-detail') {
      copy.textContent = "Pick an opponent below to load film. I'll surface the play-by-play, belief-state movement, and the moment your agent adapted.";
      return;
    }
    copy.textContent = 'Ask for a coordinator style, accept the structured proposal, then inspect the saved draft config.';
  }

  function renderFilmRoomEmptyState(route) {
    const dock = $('proposalDock');
    if (!dock) return;
    if (route.name !== 'replays') {
      if (dock.dataset.routeEmpty === 'film') {
        dock.innerHTML = '';
        delete dock.dataset.routeEmpty;
      }
      return;
    }
    if (dock.children.length && dock.dataset.routeEmpty !== 'film') return;
    dock.dataset.routeEmpty = 'film';
    dock.innerHTML = `<div class="chat-row">
      <span class="chat-avatar" aria-hidden="true">CB</span>
      <article class="film-card">
        <span class="film-card__icon" aria-hidden="true"><svg viewBox="0 0 16 16"><rect x="2.5" y="3.5" width="11" height="9" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M5 3.5v9M11 3.5v9M2.5 6h11M2.5 10h11" fill="none" stroke="currentColor" stroke-width="1.2"/></svg></span>
        <div class="film-card__body">
          <strong>rungame_vs_pressurelook.replay</strong>
          <span class="eyebrow">WATCH FILM</span>
        </div>
        <button class="btn btn--primary" type="button" data-open-replay="seed-42">Open</button>
      </article>
    </div>`;
    bindReplayButtons(dock);
    window.CBAssistant?.setComposerStatus?.('NO FILM LOADED');
  }

  function syncReplayChrome() {
    const replay = window.CBState?.get?.().replay;
    if (!replay) return;
    const result = replay.score?.result;
    const drawerTitle = $('drawerTitle')?.textContent || 'Offense ⇌ Defense';
    const drawerEyebrow = $('drawerEyebrow');
    if (drawerEyebrow) {
      drawerEyebrow.textContent = `FILM · ${drawerTitle}`.toUpperCase();
      drawerEyebrow.classList.toggle('is-touchdown', result === 'touchdown');
      drawerEyebrow.classList.toggle('is-stopped', result === 'stopped');
    }
    const meta = $('replayHeroMeta');
    if (meta) meta.textContent = `${replay.score?.points ?? 0} pts · ${replay.plays?.length ?? 0} plays`;
    const matchup = $('replayHeroMatchup')?.textContent;
    if (matchup) window.CBAssistant?.setComposerStatus?.(`LOADED · ${matchup.toUpperCase()}`);
    formatPlayFeedCards(replay);
  }

  function downLabel(value) {
    const n = Number(value || 1);
    if (n === 1) return '1ST';
    if (n === 2) return '2ND';
    if (n === 3) return '3RD';
    return `${n}TH`;
  }

  function playStartState(replay, index) {
    if (index > 0) return replay.plays[index - 1]?.public?.next_state || {};
    return {
      down: replay.metadata?.initial_down,
      distance: replay.metadata?.initial_distance,
      yardline: replay.metadata?.start_yardline,
    };
  }

  function formatPlayFeedCards(replay) {
    const feed = $('playFeed');
    if (!feed || !replay?.plays?.length) return;
    feed.querySelectorAll('.feed-card[data-feed-index]').forEach(card => {
      const index = Number(card.dataset.feedIndex);
      const play = replay.plays[index];
      const pub = play?.public;
      if (!pub) return;
      const start = playStartState(replay, index);
      const yards = Number(pub.yards_gained || 0);
      const yardText = `${yards >= 0 ? '+' : ''}${yards} yds`;
      const title = `<span class="feed-side">Offense -</span> ${escapeHtml(label(pub.offense_action?.concept_family))} <span class="feed-side feed-side--defense">Defense -</span> ${escapeHtml(label(pub.defense_action?.coverage_family))}`;
      const desc = `${pub.success ? 'Successful call' : 'Contained call'} · ${yardText}${pub.terminal_reason ? ` · ${label(pub.terminal_reason)}` : ''}`;
      const currentTags = card.querySelector('.feed-tags')?.innerHTML || '<span class="muted">No graph card</span>';
      const delta = play.adaptation_detail?.delta;
      const adaptationDelta = Number.isFinite(Number(delta)) ? ` · BELIEF Δ ${Number(delta) >= 0 ? '+' : ''}${Number(delta).toFixed(2)}` : '';
      const eyebrow = play.is_adaptation
        ? `ADAPTATION${adaptationDelta}`
        : `PLAY ${pub.play_index} · ${downLabel(start.down)} & ${start.distance ?? '-'} AT ${start.yardline ?? '-'}`;
      card.innerHTML = `
        <span class="feed-eyebrow">${escapeHtml(eyebrow)}</span>
        <span class="feed-body">${title}</span>
        <span class="feed-causal">${escapeHtml(desc)}</span>
        <span class="feed-tags">${play.is_adaptation ? '<span class="chip chip--insight">Insight</span><span class="chip chip--insight">Belief shift</span>' : currentTags}</span>`;
    });
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
          result: row.result || row.terminal_result || row.score?.result,
        }))
      : await loadShowcaseCards();
    renderWatchFilmCards(cards);
    bindReplayButtons();
    refreshDraftStatus();
  }

  function init() {
    if (!$('appRoot')?.hasAttribute('data-shell-root')) return;
    bindPrompts();
    bindDrawer();
    refresh().catch(() => {
      renderEmpty('railIdentities', 'railIdentityStatus', 'Backend offline. Opponents unavailable.');
      renderEmpty('railSessions', 'railSessionStatus', 'Backend offline. Past runs unavailable.');
    });
    window.CBState?.subscribe?.(() => setTimeout(syncReplayChrome, 0));
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
