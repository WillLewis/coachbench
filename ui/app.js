const runtime = { graphCards: {}, conceptLabels: {}, profiles: {}, auto: null, autoScrolling: false, skipNextRouteScroll: false, sharedLoaded: false, replayIndex: null, replaySources: {}, replayId: null };
const $ = id => document.getElementById(id);
const fallbackReplaySources = {
  'seed-42': 'demo_replay.json',
  'static-proof': 'static_proof_replay.json',
};
const inspectorTabs = [
  { id: 'outcome', label: 'Outcome' },
  { id: 'resources', label: 'Resources' },
  { id: 'beliefs', label: 'Beliefs' },
  { id: 'graph', label: 'Graph Evidence' },
];
const garageControlSections = {
  identity: ['offensive_archetype', 'defensive_archetype'],
  strategy: ['risk_tolerance', 'adaptation_speed', 'pressure_punish_threshold', 'screen_trigger_confidence', 'explosive_shot_tolerance', 'run_pass_tendency', 'disguise_sensitivity', 'counter_repeat_tolerance'],
  resource: ['resource_conservation'],
};
const numericControls = new Set(['adaptation_speed', 'pressure_punish_threshold', 'screen_trigger_confidence', 'explosive_shot_tolerance', 'disguise_sensitivity', 'counter_repeat_tolerance']);
const garageDraftPrefix = 'coachbench.garageDraft.';
const motionQuery = typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
const reduced = () => typeof document !== 'undefined' && document.documentElement.classList.contains('reduced-motion');
const label = key => runtime.conceptLabels[key] || String(key || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const value = item => item === null || item === undefined || item === '' ? '-' : item;
const pct = raw => Math.round(Number(raw || 0) * 100);
const currentReplay = () => CBState.get().replay;
const escapeHtml = raw => String(raw ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const truncate = (raw, max = 64) => String(raw || '').length > max ? `${String(raw).slice(0, max - 1)}…` : String(raw || '');

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} ${response.status}`);
  return response.json();
}

async function loadReplayIndex() {
  if (runtime.replayIndex) return runtime.replayIndex;
  const index = await fetchJson('replay_index.json').catch(() => []);
  runtime.replayIndex = Array.isArray(index) ? index : [];
  runtime.replaySources = {
    ...fallbackReplaySources,
    ...Object.fromEntries(runtime.replayIndex.map(item => [item.id, item.path])),
  };
  return runtime.replayIndex;
}

async function loadSharedData() {
  if (runtime.sharedLoaded) return;
  const [graph, concepts, loadedProfiles] = await Promise.all([
    fetchJson('../graph/redzone_v0/interactions.json').catch(() => ({ interactions: [] })),
    fetchJson('../graph/redzone_v0/concepts.json').catch(() => ({ offense: [], defense: [] })),
    fetchJson('../agent_garage/profiles.json').catch(() => ({})),
  ]);
  runtime.graphCards = Object.fromEntries((graph.interactions || []).map(card => [card.id, card]));
  runtime.conceptLabels = {};
  [...(concepts.offense || []), ...(concepts.defense || [])].forEach(item => runtime.conceptLabels[item.id] = item.label || item.name);
  runtime.profiles = loadedProfiles;
  runtime.sharedLoaded = true;
}

async function loadReplay(id, playParam) {
  await loadSharedData();
  await loadReplayIndex();
  const source = runtime.replaySources[id] || fallbackReplaySources[id] || showcaseReplaySource(id);
  if (!source) {
    renderReplayNotFound(id);
    return;
  }
  const rawReplay = await fetchJson(source).catch(error => {
    if (id === 'seed-42') return fetchJson(fallbackReplaySources['static-proof']);
    throw error;
  });
  const replay = annotateReplay(rawReplay);
  runtime.replayId = id;
  CBState.set({
    replay,
    selectedIndex: playToIndex(playParam, replay.plays.length),
    garageState: structuredClone(replay.agent_garage_config || {}),
    autoplay: !reduced(),
  });
  $('replayNotFound').hidden = true;
  $('replayDetailContent').hidden = false;
  renderAll();
}

function showcaseReplaySource(id) {
  const match = String(id || '').match(/^seed-(\d+)$/);
  return match ? `showcase_replays/seed_${match[1]}.json` : null;
}

function renderReplayNotFound(id) {
  runtime.auto?.stop();
  runtime.replayId = null;
  CBState.set({ replay: null, selectedIndex: 0, garageState: {}, autoplay: false });
  $('replayDetailContent').hidden = true;
  $('replayNotFound').hidden = false;
  $('replayNotFound').innerHTML = `<div class="panel"><h1>Replay not found</h1><p class="subhead">${CBEmptyStates.notFoundReplay(id)}</p><a class="btn" href="#/replays">Back to replays</a></div>`;
}

function renderAll() {
  renderHeader();
  renderCompactAgentCard();
  renderDailySlate();
  renderRosterStrengths();
  renderPlayFeed();
  renderDriveSummary();
  renderFilmRoom();
  renderInspectorTabs();
  setupOverlay();
  setupFeedAutoplay();
  selectPlay(CBState.get().selectedIndex, { syncHash: false, scroll: false, source: 'route' });
  mountRows(document);
  if (!reduced()) runtime.auto.start();
}

function syncMotionPreference() {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('reduced-motion', motionQuery.matches);
  if (motionQuery.matches) {
    runtime.auto?.stop();
    CBState.set({ autoplay: false });
  }
}

function motionMs(token) {
  if (typeof document === 'undefined' || typeof getComputedStyle !== 'function') return 0;
  const raw = getComputedStyle(document.documentElement).getPropertyValue(token).trim();
  if (raw.endsWith('ms')) return Number(raw.slice(0, -2)) || 0;
  if (raw.endsWith('s')) return (Number(raw.slice(0, -1)) || 0) * 1000;
  return 0;
}

function setActiveRoute(route) {
  document.querySelectorAll('[data-route]').forEach(section => {
    section.hidden = section.dataset.route !== route.name;
  });
  document.querySelectorAll('[data-route-link]').forEach(link => {
    const active = link.dataset.routeLink === route.name || (link.dataset.routeLink === 'replays' && route.name === 'replay-detail');
    link.classList.toggle('active', active);
    link.setAttribute('aria-current', active ? 'page' : 'false');
  });
}

async function handleRoute(route) {
  setActiveRoute(route);
  if (route.name !== 'replay-detail') runtime.auto?.stop();
  if (route.name === 'replays') {
    await renderGallery();
  } else if (route.name === 'replay-detail') {
    if (runtime.replayId === route.params.id && currentReplay()) {
      const shouldScroll = !runtime.skipNextRouteScroll;
      runtime.skipNextRouteScroll = false;
      selectPlay(playToIndex(route.params.play, currentReplay().plays.length), { syncHash: false, scroll: shouldScroll, source: 'route' });
    } else {
      await loadReplay(route.params.id, route.params.play);
    }
  } else if (route.name === 'garage') {
    await loadSharedData();
    ensureGarageDefaults();
    renderGaragePage(route.params);
  } else if (route.name === 'reports') {
    renderReports(route.params.compare);
  } else if (route.name === 'arena') {
    renderRouteStub('arenaRouteCopy', 'Coming in Pass 8.');
  }
  renderCompareTray();
}

async function renderGallery() {
  const target = $('replayGallery');
  if (!target) return;
  const index = await loadReplayIndex();
  if (!index.length) {
    target.innerHTML = `<div class="panel empty-state"><p class="subhead">${CBEmptyStates.emptyReplays()}</p><code>python scripts/run_showcase.py --seed 42 --out data/demo_replay.json --copy-ui</code></div>`;
    return;
  }
  target.innerHTML = index.map(renderReplayCard).join('');
  target.querySelectorAll('[data-compare-id]').forEach(button => {
    button.onclick = event => {
      event.preventDefault();
      event.stopPropagation();
      toggleCompare(button.dataset.compareId);
    };
  });
  mountRows(target);
}

function renderRouteStub(id, copy) {
  $(id).textContent = copy;
}

function renderReports(compare) {
  const ids = String(compare || '').split(',').filter(Boolean);
  renderRouteStub('reportsRouteCopy', ids.length ? `Coming in Pass 7. Reserved comparison: ${ids.join(', ')}.` : 'Coming in Pass 7.');
}

function renderReplayCard(item) {
  const pinned = CBState.get().pinnedForCompare.includes(item.id);
  const seed = item.id === 'static-proof' ? 'STATIC PROOF' : `SEED ${item.seed}`;
  return `<article class="replay-card panel" data-gallery-card="${escapeHtml(item.id)}">
    <button class="compare-toggle" type="button" data-compare-id="${escapeHtml(item.id)}" aria-pressed="${pinned}">${pinned ? 'Pinned' : '+ Compare'}</button>
    <a class="replay-card-main" href="#/replays/${encodeURIComponent(item.id)}">
      <span class="eyebrow" data-card-field="eyebrow">${seed} · RED ZONE · ${item.plays} PLAYS</span>
      <strong data-card-field="matchup">${escapeHtml(item.matchup)}</strong>
      <span class="result-row" data-card-field="result"><span>${escapeHtml(item.result)}</span><em>${escapeHtml(item.outcome_chip || label(item.terminal_result))}</em></span>
      <span class="tier-row"><span class="tier-chip" data-tier-chip="offense">${escapeHtml(item.offense_label || 'Team A coordinator agent')} · Tier ${item.tier_offense}</span><span class="tier-chip" data-tier-chip="defense">${escapeHtml(item.defense_label || 'Team B coordinator agent')} · Tier ${item.tier_defense}</span></span>
      ${gallerySparkline(item.sparkline || [])}
      <span class="metric-row"><span data-card-field="invalid_actions">${item.invalid_actions} invalid actions</span><span data-card-field="top_graph_event">${escapeHtml(truncate(item.top_graph_event))}</span></span>
    </a>
  </article>`;
}

function gallerySparkline(values) {
  const nums = values.length ? values.map(Number) : [0];
  const min = Math.min(...nums), max = Math.max(...nums), range = max - min || 1;
  const x = i => nums.length === 1 ? 4 : 4 + (i / (nums.length - 1)) * 88;
  const y = raw => 20 - ((raw - min) / range) * 16;
  const points = nums.map((raw, i) => `${x(i).toFixed(2)},${y(raw).toFixed(2)}`).join(' ');
  return `<svg class="gallery-sparkline" width="96" height="24" viewBox="0 0 96 24" aria-hidden="true" data-card-field="sparkline"><path class="gallery-spark-line" d="M${points.replaceAll(' ', ' L')}"></path></svg>`;
}

function toggleCompare(id) {
  const pins = CBState.get().pinnedForCompare;
  const next = pins.includes(id) ? pins.filter(item => item !== id) : [...pins, id].slice(0, 4);
  CBState.set({ pinnedForCompare: next });
  renderGallery();
  renderCompareTray();
}

function removeCompare(id) {
  CBState.set({ pinnedForCompare: CBState.get().pinnedForCompare.filter(item => item !== id) });
  renderGallery();
  renderCompareTray();
}

function renderCompareTray() {
  const tray = $('compareTray');
  if (!tray) return;
  const pins = CBState.get().pinnedForCompare;
  tray.hidden = !pins.length;
  const disabled = pins.length < 2;
  tray.innerHTML = `<div class="compare-pins">${pins.map(id => `<span class="pin-chip">${escapeHtml(id)}<button type="button" data-unpin="${escapeHtml(id)}" aria-label="Remove ${escapeHtml(id)}">×</button></span>`).join('')}</div>
    <button id="compareAction" class="btn" type="button" ${disabled ? 'disabled title="Pin at least two replays to compare."' : ''}>Compare ${pins.length}</button>`;
  tray.querySelectorAll('[data-unpin]').forEach(button => button.onclick = () => removeCompare(button.dataset.unpin));
  const action = $('compareAction');
  if (action) action.onclick = () => { if (!disabled) CBRouter.go('reports', { compare: pins.join(',') }); };
}

function playToIndex(playParam, count) {
  const parsed = Number(playParam || 1);
  return Math.max(0, Math.min(count - 1, Number.isFinite(parsed) ? parsed - 1 : 0));
}

function annotateReplay(rawReplay) {
  const replay = structuredClone(rawReplay);
  const reasons = CBAdaptation.classifyAdaptationReasons(replay.plays, runtime.graphCards);
  replay.plays = replay.plays.map((play, index) => ({
    ...play,
    is_adaptation: Boolean(reasons[index]),
    adaptation_reason: reasons[index] || null,
    adaptation_detail: reasons[index] ? adaptationDetail(replay.plays, index, reasons[index]) : null,
  }));
  return replay;
}

function adaptationDetail(plays, index, reason) {
  if (reason === 'graph-fire') {
    const prior = new Set(plays.slice(0, index).flatMap(play => play.public.graph_card_ids || []));
    const cardId = (plays[index].public.graph_card_ids || []).find(id => !prior.has(id));
    return { type: reason, card_id: cardId, card_label: cardLabel(cardId) };
  }
  if (reason === 'belief-shift') {
    const shift = largestBeliefShift(plays[index], plays[index - 1]);
    return { type: reason, key: shift?.key, delta: shift?.delta || 0 };
  }
  const priorCall = plays[index - 1]?.public.offense_action?.concept_family;
  const newCall = plays[index].public.offense_action?.concept_family;
  const priorDefense = plays[index - 1]?.public.defense_action?.coverage_family;
  const newDefense = plays[index].public.defense_action?.coverage_family;
  return newCall !== priorCall
    ? { type: reason, prior_call: priorCall, new_call: newCall }
    : { type: reason, prior_call: priorDefense, new_call: newDefense };
}

function cardLabel(cardId) {
  return runtime.graphCards[cardId]?.name || label(cardId);
}

function playBeliefs(play) {
  return play.public.beliefs || play.offense_observed?.belief_after || {};
}

function largestBeliefShift(play, prior) {
  if (!prior) return null;
  const current = playBeliefs(play);
  const before = playBeliefs(prior);
  return [...new Set([...Object.keys(current), ...Object.keys(before)])]
    .map(key => ({ key, delta: Number(current[key] || 0) - Number(before[key] || 0) }))
    .filter(item => Math.abs(item.delta) >= 0.10)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))[0] || null;
}

function renderHeader() {
  const replay = currentReplay();
  const staticMode = replay.metadata.mode === 'static_proof';
  $('modeBanner').textContent = staticMode
    ? 'Phase 0B static schema/UI proof - not an engine-generated benchmark result.'
    : 'Engine-generated replay';
  $('modeBanner').classList.toggle('static-proof', staticMode);
  morphText($('resultLabel'), label(replay.score.result));
  morphText($('pointsLabel'), `${replay.score.points} pts`);
  $('episodeLabel').textContent = replay.metadata.episode_id;
  if (replay.score.result === 'touchdown') flashScore('good');
  if (replay.score.result === 'stopped') flashScore('warn');
}

function kvRows(obj, keys = Object.keys(obj || {})) {
  return keys.map(key => `<div class="kv"><span>${label(key)}</span><span>${value(formatValue(obj[key]))}</span></div>`).join('');
}

function formatValue(raw) {
  if (Array.isArray(raw)) return raw.map(label).join(', ');
  if (typeof raw === 'object' && raw) return JSON.stringify(raw);
  return typeof raw === 'string' ? label(raw) : raw;
}

function renderPlayFeed() {
  const replay = currentReplay();
  const feed = $('playFeed');
  feed.innerHTML = replay.plays.map((play, index) => feedCard(play, index)).join('');
  feed.querySelectorAll('[data-feed-index]').forEach(card => {
    card.onclick = () => {
      pauseForUser();
      selectPlay(Number(card.dataset.feedIndex), { syncHash: true, scroll: false, source: 'click' });
    };
  });
  feed.onscroll = () => {
    if (!runtime.autoScrolling && runtime.auto?.isRunning()) pauseForUser();
  };
  $('resumeFeed').onclick = () => runtime.auto?.start();
}

function feedCard(play, index) {
  const pub = play.public;
  const offense = label(pub.offense_action.concept_family);
  const defense = label(pub.defense_action.coverage_family);
  const yards = Number(pub.yards_gained || 0);
  const yardText = `${yards >= 0 ? '+' : ''}${yards} yd`;
  const outcome = `${pub.success ? 'Success' : 'No success'} · ${yardText}${pub.terminal_reason ? ` · ${label(pub.terminal_reason)}` : ''}`;
  const cards = (pub.graph_card_ids || []).map(id => `<span class="chip" title="${escapeHtml(id)}">${escapeHtml(cardLabel(id))}</span>`).join('');
  const turningPoint = currentReplay().film_room?.turning_point?.play_index === pub.play_index;
  const adaptation = play.is_adaptation;
  return `<button class="feed-card ${adaptation ? 'is-adaptation' : ''}" type="button" role="listitem" data-feed-index="${index}" aria-current="false">
    <span class="feed-eyebrow">${adaptation ? `ADAPTATION · PLAY ${pub.play_index}` : `PLAY ${pub.play_index} · ${offense} vs ${defense}`}${turningPoint ? ' · ★ TURNING POINT' : ''}</span>
    <span class="feed-body">${outcome}</span>
    ${adaptation ? `<span class="feed-causal">${causalLine(play)}</span>` : ''}
    <span class="feed-tags">${cards || '<span class="muted">No graph card</span>'}</span>
  </button>`;
}

function causalLine(play) {
  const detail = play.adaptation_detail || {};
  if (play.adaptation_reason === 'graph-fire') return `Trigger: ${detail.card_label || 'Graph card'} fired`;
  if (play.adaptation_reason === 'belief-shift') return `Belief: ${label(detail.key)} ${detail.delta >= 0 ? '+' : ''}${Math.round(Number(detail.delta || 0) * 100)}pp`;
  if (play.adaptation_reason === 'counter-call') return `Adjustment: ${label(detail.prior_call)} → ${label(detail.new_call)}`;
  return '';
}

function selectPlay(index, options = {}) {
  const { syncHash = false, scroll = false, source = 'user' } = options;
  CBState.set({ selectedIndex: index });
  const replay = currentReplay();
  const play = replay.plays[index];
  const prior = index > 0 ? replay.plays[index - 1] : null;
  document.querySelectorAll('[data-feed-index]').forEach(card => {
    const active = Number(card.dataset.feedIndex) === index;
    card.classList.toggle('active', active);
    card.setAttribute('aria-current', active ? 'true' : 'false');
  });
  restartAutoplayProgress();
  renderBall(play.public.next_state.yardline, play.public.terminal_reason);
  $('driveState').textContent = `${play.public.next_state.down} & ${play.public.next_state.distance} at ${play.public.next_state.yardline}`;
  $('inspectorPlayLabel').textContent = `Play ${play.public.play_index}`;
  renderInspectorPanel(play, prior);
  if (scroll) scrollFeedCard(index);
  if (syncHash) {
    runtime.skipNextRouteScroll = source === 'click';
    CBRouter.go('replay-detail', { id: runtime.replayId, play: play.public.play_index });
  }
}

function scrollFeedCard(index) {
  const card = document.querySelector(`[data-feed-index="${index}"]`);
  if (!card) return;
  runtime.autoScrolling = true;
  card.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'nearest' });
  setTimeout(() => { runtime.autoScrolling = false; }, motionMs('--motion-belief-pulse'));
}

function renderBall(yardline, terminalReason) {
  const clamped = Math.max(0, Math.min(25, Number(yardline)));
  const left = 8 + ((25 - clamped) / 25) * 84;
  const ball = $('ball');
  ball.style.left = `${left}%`;
  ball.classList.toggle('touchdown', terminalReason === 'touchdown');
  if (!reduced()) {
    ball.classList.remove('move');
    void ball.offsetWidth;
    ball.classList.add('move');
  }
}

function activeInspectorTab() {
  const current = CBState.get().activeInspectorTab;
  return inspectorTabs.some(tab => tab.id === current) ? current : 'outcome';
}

function renderInspectorTabs() {
  document.querySelectorAll('[data-inspector-tab]').forEach((button, index) => {
    button.onclick = () => activateInspectorTab(button.dataset.inspectorTab);
    button.onkeydown = event => handleInspectorKey(event, index);
  });
  updateInspectorTabs();
}

function activateInspectorTab(tabId) {
  if (!inspectorTabs.some(tab => tab.id === tabId)) return;
  CBState.set({ activeInspectorTab: tabId });
  updateInspectorTabs();
  const replay = currentReplay();
  if (!replay) return;
  const index = CBState.get().selectedIndex;
  renderInspectorPanel(replay.plays[index], index > 0 ? replay.plays[index - 1] : null);
}

function handleInspectorKey(event, index) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End', 'Enter', ' '].includes(event.key)) return;
  event.preventDefault();
  if (event.key === 'Enter' || event.key === ' ') {
    activateInspectorTab(event.currentTarget.dataset.inspectorTab);
    return;
  }
  const nextIndex = event.key === 'Home'
    ? 0
    : event.key === 'End'
      ? inspectorTabs.length - 1
      : (index + (event.key === 'ArrowRight' ? 1 : -1) + inspectorTabs.length) % inspectorTabs.length;
  document.querySelector(`[data-inspector-tab="${inspectorTabs[nextIndex].id}"]`)?.focus();
}

function updateInspectorTabs() {
  const active = activeInspectorTab();
  document.querySelectorAll('[data-inspector-tab]').forEach(button => {
    const selected = button.dataset.inspectorTab === active;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-selected', selected ? 'true' : 'false');
    button.tabIndex = selected ? 0 : -1;
  });
  const panel = $('inspectorPanel');
  if (panel) {
    panel.dataset.activeTab = active;
    panel.setAttribute('aria-labelledby', `inspector-tab-${active}`);
  }
}

function renderInspectorPanel(play, prior) {
  const panel = $('inspectorPanel');
  if (!panel || !play) return;
  const tab = activeInspectorTab();
  const pub = play.public;
  const views = {
    outcome: () => renderOutcome(play, prior),
    resources: () => renderResources(pub.resource_budget_snapshot, prior && prior.public.resource_budget_snapshot),
    beliefs: () => renderBeliefs(play, prior),
    graph: () => renderGraphCards(pub.graph_card_ids || []),
  };
  panel.classList.remove('inspector-fade');
  panel.innerHTML = (views[tab] || views.outcome)();
  panel.dataset.activeTab = tab;
  panel.setAttribute('aria-labelledby', `inspector-tab-${tab}`);
  if (!reduced()) {
    void panel.offsetWidth;
    panel.classList.add('inspector-fade');
  }
}

function renderOutcome(play) {
  const pub = play.public || play;
  const result = pub.validation_result;
  const yardText = `${Number(pub.yards_gained || 0) >= 0 ? '+' : ''}${pub.yards_gained || 0} yd`;
  return `<div class="outcome-stack">
    <div class="outcome-hero">
      <div>
        <p class="eyebrow">${pub.success ? 'Success' : 'No success'}</p>
        <strong>${yardText}</strong>
      </div>
      <span class="validation-badge ${result?.ok ? 'is-ok' : 'is-warn'}">${result ? (result.ok ? 'Accepted' : 'Rejected') : 'No validation data'}</span>
    </div>
    <div class="outcome-grid">
      <div><h3>Offense Call</h3>${kvRows(pub.offense_action, Object.keys(pub.offense_action || {}))}</div>
      <div><h3>Defense Call</h3>${kvRows(pub.defense_action, Object.keys(pub.defense_action || {}))}</div>
    </div>
    <div class="kv"><span>Expected Value Delta</span><span>${pub.expected_value_delta}</span></div>
    <div class="kv"><span>Terminal Reason</span><span>${value(label(pub.terminal_reason))}</span></div>
    <div class="kv"><span>Next State</span><span>${pub.next_state.down} & ${pub.next_state.distance} at ${pub.next_state.yardline}</span></div>
    <h3>Events</h3>
    ${renderEvents(pub.events || [])}
  </div>`;
}

function resourceRows(snapshot, prior, side) {
  const before = snapshot[`${side}_before`] || {}, cost = snapshot[`${side}_cost`] || {}, remaining = snapshot[`${side}_remaining`] || {};
  const priorRemaining = prior ? prior[`${side}_remaining`] || {} : null;
  return Object.keys(before).map(resource => ({
    resource, before: before[resource], cost: cost[resource] || 0, remaining: remaining[resource],
    delta: priorRemaining ? remaining[resource] - priorRemaining[resource] : null,
  }));
}

function resourceTable(snapshot, prior, side) {
  return `<div class="resource-card"><h3>${label(side)}</h3><table class="matrix"><thead><tr><th>Resource</th><th>Before</th><th>Cost</th><th>Remaining</th><th>Delta</th></tr></thead><tbody>${
    resourceRows(snapshot, prior, side).map(row => `<tr><td>${label(row.resource)}</td><td>${row.before}</td><td>${row.cost}</td><td>${row.remaining}</td><td class="${row.delta < 0 ? 'delta-neg' : row.delta > 0 ? 'delta-pos' : ''}">${row.delta === null ? '' : row.delta}</td></tr>`).join('')
  }</tbody></table></div>`;
}

function renderResources(snapshot, prior) {
  return `<div class="resource-grid">${resourceTable(snapshot, prior, 'offense')}${resourceTable(snapshot, prior, 'defense')}</div>`;
}

function renderGraphCards(ids) {
  return ids.map(id => graphEvidenceHtml(runtime.graphCards[id], id)).join('') || `<p class="muted">${CBEmptyStates.emptyGraphEvidence()}</p>`;
}

function graphCardHtml(card, id) {
  if (!card) return `<p class="muted">Card not found: ${id}</p>`;
  const tags = (card.tactical_events || []).map(event => event.tag || event).join(', ');
  return `<div class="card-ref"><h3>${card.name}</h3>${kvRows({ id: card.id, counters: card.counters || [], limitations: (card.limitations || []).join(' '), events: tags }, ['id', 'counters', 'limitations', 'events'])}</div>`;
}

function graphEvidenceHtml(card, id) {
  if (!card) return `<p class="muted">Card not found: ${id}</p>`;
  const counters = (card.counters || []).map(label).join(', ') || '-';
  return `<div class="graph-evidence-card">
    <h3>${escapeHtml(card.name || label(id))}</h3>
    <div class="kv"><span>Card Id</span><span><code>${escapeHtml(card.id || id)}</code></span></div>
    <div class="kv"><span>Counters</span><span>${escapeHtml(counters)}</span></div>
  </div>`;
}

function renderBeliefs(play, prior) {
  const beliefs = playBeliefs(play);
  const priorBeliefs = prior ? playBeliefs(prior) : {};
  return Object.entries(beliefs).map(([key, raw]) => {
    const percent = pct(raw);
    const delta = prior ? percent - pct(priorBeliefs[key]) : null;
    const changed = delta !== null && Math.abs(delta) >= 10;
    const deltaText = delta === null ? '' : ` · <span class="${delta < 0 ? 'delta-neg' : delta > 0 ? 'delta-pos' : ''}">${delta >= 0 ? '+' : ''}${delta}pp</span>`;
    return `<div class="bar"><label><span>${label(key)}</span><span>${percent}%${deltaText}</span></label><div class="meter"><div class="fill ${changed ? 'glow' : ''}" style="width:${percent}%"></div></div></div>`;
  }).join('') || '<p class="muted">No belief data on this play.</p>';
}

function renderEvents(events) {
  return events.length
    ? events.map(event => `<div class="event-block"><span class="chip">${label(event.tag)}</span><p><strong>${event.graph_card_id}</strong><br>${event.description || ''}</p></div>`).join('')
    : '<p class="muted">No public graph event on this play.</p>';
}

function renderDriveSummary() {
  const replay = currentReplay();
  const last = replay.plays.at(-1).public;
  const points = replay.plays.map(play => Number(play.public.expected_value_delta || 0));
  const best = replay.plays.reduce((winner, play) =>
    Math.abs(play.public.expected_value_delta || 0) > Math.abs(winner.public.expected_value_delta || 0) ? play : winner
  , replay.plays[0]);
  const recap = `${label(replay.score.result)} on play ${last.play_index} after ${replay.plays.length} plays`;
  $('driveSummary').innerHTML = `
    <div class="kv"><span>Result</span><strong>${label(replay.score.result)}</strong></div>
    <div class="kv"><span>Points</span><span>${replay.score.points}</span></div>
    <div class="kv"><span>Plays Played</span><span>${replay.plays.length}</span></div>
    <div class="kv"><span>Terminal Reason</span><span>${value(label(last.terminal_reason))}</span></div>
    ${sparkline(points)}
    <div class="kv"><span>Best Play</span><span>Play ${best.public.play_index} (${Number(best.public.expected_value_delta).toFixed(2)})</span></div>
    <div class="kv"><span>Drive Recap</span><span>${recap}</span></div>
  `;
}

function sparkline(values) {
  if (!values.length) return '';
  const min = Math.min(...values), max = Math.max(...values), range = max - min || 1;
  const x = i => 18 + (i / Math.max(1, values.length - 1)) * 172;
  const y = v => 118 - ((v - min) / range) * 82;
  const pts = values.map((v, i) => `${x(i)},${y(v)}`).join(' ');
  const zeroY = min <= 0 && max >= 0 ? y(0) : y(min);
  const bestIndex = values.reduce((winner, v, i) => Math.abs(v) > Math.abs(values[winner]) ? i : winner, 0);
  const bestValue = values[bestIndex];
  const ticks = values.map((_, i) => `<text class="spark-tick" x="${x(i)}" y="144" text-anchor="middle">${i + 1}</text>`).join('');
  return `<div class="sparkline-wrap"><svg class="sparkline" viewBox="0 0 200 150" preserveAspectRatio="none">
    <text class="spark-label" x="0" y="20">EP delta</text>
    <line class="spark-axis" x1="16" x2="192" y1="${zeroY}" y2="${zeroY}"></line>
    <path class="draw-on-mount" d="M${pts.replaceAll(' ', ' L')}" />
    <circle class="spark-dot" cx="${x(bestIndex)}" cy="${y(bestValue)}" r="4"></circle>
    <text class="spark-dot-label" x="${Math.min(172, x(bestIndex) + 6)}" y="${Math.max(12, y(bestValue) - 7)}">${bestValue >= 0 ? '+' : ''}${bestValue.toFixed(2)}</text>
    ${ticks}
  </svg></div>`;
}

function renderFilmRoom() {
  const replay = currentReplay();
  $('filmRoom').innerHTML = renderFilmRoomHtml(replay);
}

function renderFilmRoomHtml(replay) {
  const room = replay.film_room || {};
  const nextTry = room.next_try || room.next_adjustment;
  if (!room.turning_point || !nextTry) {
    return '<p class="muted">No turning point this drive.</p>';
  }
  const turningCards = room.turning_point.graph_card_ids || [];
  const primaryCardId = turningCards[0];
  const evidence = filmRoomEvidence(replay, nextTry);
  return `<section class="film-compressed">
    <div class="film-line">
      <h3>Turning Point</h3>
      <p>Play ${room.turning_point.play_index} · ${escapeHtml(shortCardLabel(primaryCardId))}</p>
    </div>
    <div class="film-line">
      <h3>Why It Mattered</h3>
      <p>${escapeHtml(filmRoomWhyItMattered(room, primaryCardId))}</p>
    </div>
    <div class="film-next">
      <h3>Next Try</h3>
      <p>${escapeHtml(displayNextTry(nextTry))}</p>
    </div>
    <div class="film-evidence">
      <h3>Evidence</h3>
      ${evidence.hasDirectCounter ? '' : '<p class="muted compact">Recommendation derived from sequencing — no direct counter card.</p>'}
      <ul class="film-evidence-list">${evidence.items.map(item => `<li title="${escapeHtml(item.card_id)}">${escapeHtml(item.label)} · play ${item.play_index}</li>`).join('')}</ul>
    </div>
    <details class="film-notes">
      <summary>View full notes</summary>
      <div class="film-notes-scroll">${filmRoomFullNotes(room)}</div>
    </details>
  </section>`;
}

function displayNextTry(raw) {
  return String(raw || '').replace(/^Next try:\s*/i, '');
}

function recommendedCounterLabel(raw) {
  return displayNextTry(raw).split(' to counter ')[0].trim();
}

function filmRoomWhyItMattered(room, cardId) {
  if (room.why_it_mattered) return room.why_it_mattered;
  const cardName = cardLabel(cardId);
  return (room.notes || []).find(note => String(note).includes(cardName)) || (room.notes || [])[0] || room.headline || 'Film Room feedback unavailable.';
}

function shortCardLabel(cardId) {
  const full = cardLabel(cardId);
  return full.length > 56 ? `${full.slice(0, 55)}…` : full;
}

function filmRoomEvidence(replay, nextTry) {
  const room = replay.film_room || {};
  const recommended = recommendedCounterLabel(nextTry);
  const records = new Map();
  const playByIndex = new Map((replay.plays || []).map(play => [Number(play.public?.play_index), play]));
  const addRecord = (cardId, playIndex) => {
    if (!cardId || !runtime.graphCards[cardId]) return;
    const play = playByIndex.get(Number(playIndex));
    const leverage = Math.abs(Number(play?.public?.expected_value_delta || 0));
    const record = records.get(cardId) || { card_id: cardId, play_index: Number(playIndex) || 0, max_leverage: 0 };
    record.play_index = Math.min(record.play_index || Number(playIndex) || 0, Number(playIndex) || record.play_index || 0);
    record.max_leverage = Math.max(record.max_leverage, leverage);
    records.set(cardId, record);
  };
  (room.adaptation_chain || []).forEach(entry => addRecord(entry.graph_card_id, entry.play_index));
  (replay.plays || []).forEach(play => (play.public?.graph_card_ids || []).forEach(cardId => addRecord(cardId, play.public.play_index)));
  const all = [...records.values()].map(record => ({
    ...record,
    label: cardLabel(record.card_id),
    direct: cardCountersContain(record.card_id, recommended),
  }));
  const direct = all.filter(item => item.direct);
  const hasDirectCounter = direct.length > 0;
  const candidates = hasDirectCounter
    ? all
    : all.filter(item => (room.turning_point?.graph_card_ids || []).includes(item.card_id));
  const ranked = (candidates.length ? candidates : all)
    .sort((a, b) => Number(b.direct) - Number(a.direct) || b.max_leverage - a.max_leverage || a.play_index - b.play_index)
    .slice(0, 4)
    .sort((a, b) => Number(b.direct) - Number(a.direct) || a.play_index - b.play_index);
  return { hasDirectCounter, items: ranked };
}

function cardCountersContain(cardId, recommended) {
  if (!recommended) return false;
  return (runtime.graphCards[cardId]?.counters || []).some(counter => counter === recommended || label(counter) === recommended);
}

function filmRoomFullNotes(room) {
  const chain = (room.adaptation_chain || []).map(entry => `<li><strong>Play ${entry.play_index}</strong> · ${escapeHtml(entry.card_label || cardLabel(entry.graph_card_id))}<br><span class="muted">${escapeHtml(entry.offense_call || '-')} vs ${escapeHtml(entry.defense_call || '-')} · ${escapeHtml(entry.trigger_event || '-')}</span></li>`).join('');
  const notes = (room.notes || []).map(note => `<li>${escapeHtml(note)}</li>`).join('');
  const tweaks = (room.suggested_tweaks || []).map(tweak => `<li>${escapeHtml(tweak)}</li>`).join('');
  return `<h3>Adaptation Chain</h3><ul>${chain || '<li class="muted">No adaptation chain entries.</li>'}</ul><h3>Notes</h3><ul>${notes || '<li class="muted">-</li>'}</ul><h3>Suggested Tweaks</h3><ul>${tweaks || '<li class="muted">-</li>'}</ul>`;
}

function renderCompactAgentCard() {
  const target = $('agentCard');
  const replay = currentReplay();
  if (!target || !replay) return;
  const garageState = replay.agent_garage_config || {};
  const offense = garageState.offense_profile || {};
  const defense = garageState.defense_profile || {};
  const differences = compactProfileDiffs(garageState).slice(0, 3);
  target.innerHTML = `<div class="agent-card-compact">
    <div>
      <p class="eyebrow">Read-only replay config</p>
      <h3>${escapeHtml(offense.label || 'Static Baseline')} / ${escapeHtml(defense.label || 'Adaptive Counter')}</h3>
    </div>
    <span class="tier-chip">Tier 0</span>
    <p class="compact">${differences.length ? differences.map(item => `${label(item.key)} ${item.delta}`).join(' · ') : 'No local tuning over profile defaults.'}</p>
    <button id="tuneAgent" class="ghost-button" type="button">Tune Agent →</button>
  </div>`;
  $('tuneAgent').onclick = () => CBRouter.go('garage', { from: runtime.replayId || 'seed-42' });
}

function compactProfileDiffs(garageState) {
  return ['offense_profile', 'defense_profile'].flatMap(profileKey => {
    const profile = garageState[profileKey] || {};
    const defaults = profileDefaults(profileKey, profile.profile_key);
    return Object.entries(profile)
      .filter(([key, raw]) => defaults[key] !== undefined && key !== 'profile_key' && key !== 'label' && raw !== defaults[key])
      .map(([key, raw]) => ({ key, delta: typeof raw === 'number' ? `${raw > defaults[key] ? '+' : ''}${(raw - defaults[key]).toFixed(2)}` : `${label(defaults[key])} → ${label(raw)}` }));
  });
}

function profileDefaults(profileKey, key) {
  const bucket = profileKey === 'defense_profile' ? 'defense_archetypes' : 'offense_archetypes';
  return runtime.profiles[bucket]?.[key] || {};
}

function ensureGarageDefaults() {
  const state = CBState.get();
  const existing = state.garageState || {};
  if (existing.offense_profile && existing.defense_profile) {
    CBState.set({ garageDrafts: loadGarageDrafts() });
    return;
  }
  const offenseKey = Object.keys(runtime.profiles.offense_archetypes || {})[0];
  const defenseKey = Object.keys(runtime.profiles.defense_archetypes || {})[0];
  CBState.set({
    garageState: {
      source: 'agent_garage_profiles_v0',
      offense_profile: { ...(runtime.profiles.offense_archetypes?.[offenseKey] || {}), profile_key: offenseKey },
      defense_profile: { ...(runtime.profiles.defense_archetypes?.[defenseKey] || {}), profile_key: defenseKey },
      draft_controls: {},
    },
    garageDrafts: loadGarageDrafts(),
  });
}

function renderGaragePage(params = {}) {
  const from = params.from || runtime.replayId || 'seed-42';
  $('garageRouteCopy').textContent = `Tune a fictional coordinator agent, then return to ${from}.`;
  renderTierSelector();
  renderGarageControls();
  renderRuleBuilder();
  renderGarageActions();
  renderGarageDrafts();
  mountRows(document.querySelector('[data-route="garage"]'));
}

function renderTierSelector() {
  document.querySelectorAll('[name="garage_tier"]').forEach(input => {
    input.checked = input.value === CBState.get().garageTier;
    input.onchange = () => {
      CBState.set({ garageTier: input.value });
      renderGaragePage(CBRouter.current().params);
    };
  });
}

function renderGarageControls() {
  const tier = CBState.get().garageTier;
  const sections = {
    identity: $('garageIdentityControls'),
    strategy: $('garageStrategyControls'),
    resource: $('garageResourceControls'),
  };
  Object.entries(sections).forEach(([section, target]) => {
    const keys = tier === 'remote_endpoint' && section !== 'identity' ? [] : garageControlSections[section];
    target.innerHTML = keys.length
      ? keys.map(key => garageControlRow(key)).join('')
      : '<p class="muted compact">This tier uses endpoint-owned strategy; local controls are hidden.</p>';
  });
  document.querySelectorAll('[data-garage-control]').forEach(input => {
    input.oninput = updateGarageControl;
    input.onchange = updateGarageControl;
  });
}

function garageControlRow(key) {
  const current = garageControlValue(key);
  const error = validateGarageControl(key, current);
  const message = error || 'Valid for the selected tier.';
  const field = numericControls.has(key)
    ? `<input data-garage-control="${key}" type="range" min="0" max="1" step="0.01" value="${current}">`
    : `<select data-garage-control="${key}">${garageOptions(key, current).map(item => `<option value="${escapeHtml(item.value)}" ${item.value === current ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('')}</select>`;
  return `<label class="control-row ${error ? 'has-error' : ''}">
    <span class="label">${label(key)}</span>
    ${field}
    <small class="help-text">${garageHelp(key)}</small>
    <small class="validation-message">${message}</small>
  </label>`;
}

function garageOptions(key, current) {
  if (key === 'offensive_archetype') return archetypeOptions('offense_archetypes', current);
  if (key === 'defensive_archetype') return archetypeOptions('defense_archetypes', current);
  if (key === 'risk_tolerance') return ['low', 'medium_low', 'medium', 'medium_high', 'high'].map(value => ({ value, label: label(value) }));
  if (key === 'resource_conservation') return ['low', 'balanced', 'high'].map(value => ({ value, label: label(value) }));
  if (key === 'run_pass_tendency') return ['balanced_pass', 'pass_heavy', 'constraint_heavy', 'run_to_play_action'].map(value => ({ value, label: label(value) }));
  return [{ value: current || 'balanced', label: label(current || 'balanced') }];
}

function archetypeOptions(bucket, current) {
  const options = Object.entries(runtime.profiles[bucket] || {}).map(([value, profile]) => ({ value, label: profile.label || label(value) }));
  return options.some(item => item.value === current) ? options : [{ value: current || '', label: label(current || 'Select') }, ...options];
}

function garageHelp(key) {
  const help = {
    offensive_archetype: 'Chooses the visible offense profile defaults.',
    defensive_archetype: 'Chooses the visible defense profile defaults.',
    risk_tolerance: 'Controls conservative versus aggressive call selection.',
    adaptation_speed: 'Range 0-1; higher reacts faster to observed patterns.',
    pressure_punish_threshold: 'Range 0-1; higher waits for clearer pressure evidence.',
    screen_trigger_confidence: 'Range 0-1; minimum confidence before screen counters.',
    explosive_shot_tolerance: 'Range 0-1; higher permits more volatile calls.',
    run_pass_tendency: 'Visible tendency label for local config review.',
    disguise_sensitivity: 'Range 0-1; higher reacts more to disguise signals.',
    counter_repeat_tolerance: 'Range 0-1; lower avoids repeated counters.',
    resource_conservation: 'Controls how hard the agent spends limited resources.',
  };
  return help[key] || 'Local coordinator control.';
}

function garageControlValue(key) {
  const state = CBState.get().garageState || {};
  const draft = state.draft_controls || {};
  if (draft[key] !== undefined) return draft[key];
  if (key === 'offensive_archetype') return state.offense_profile?.profile_key || Object.keys(runtime.profiles.offense_archetypes || {})[0] || '';
  if (key === 'defensive_archetype') return state.defense_profile?.profile_key || Object.keys(runtime.profiles.defense_archetypes || {})[0] || '';
  return state.offense_profile?.[key] ?? state.defense_profile?.[key] ?? (numericControls.has(key) ? 0.5 : 'balanced');
}

function updateGarageControl(event) {
  const key = event.target.dataset.garageControl;
  const raw = event.target.type === 'range' ? Number(event.target.value) : event.target.value;
  const next = structuredClone(CBState.get().garageState || {});
  next.draft_controls = { ...(next.draft_controls || {}), [key]: raw };
  if (key === 'offensive_archetype') next.offense_profile = { ...(runtime.profiles.offense_archetypes?.[raw] || {}), profile_key: raw };
  if (key === 'defensive_archetype') next.defense_profile = { ...(runtime.profiles.defense_archetypes?.[raw] || {}), profile_key: raw };
  CBState.set({ garageState: next });
  renderGaragePage(CBRouter.current().params);
}

function validateGarageControl(key, raw) {
  if (numericControls.has(key) && (!Number.isFinite(Number(raw)) || Number(raw) < 0 || Number(raw) > 1)) return 'Enter a value from 0 to 1.';
  if ((key.includes('archetype') || key === 'risk_tolerance' || key === 'run_pass_tendency' || key === 'resource_conservation') && !raw) return 'Required.';
  return '';
}

function renderRuleBuilder() {
  const target = $('ruleChain');
  const rules = CBState.get().garageRules || [];
  target.innerHTML = rules.length ? rules.map((rule, index) => ruleRow(rule, index)).join('') : `<p class="muted compact">${CBEmptyStates.emptyAgents()}</p>`;
  target.querySelectorAll('[data-rule-field]').forEach(input => input.onchange = updateRule);
  target.querySelectorAll('[data-rule-move]').forEach(button => button.onclick = moveRule);
  target.querySelectorAll('[data-rule-delete]').forEach(button => button.onclick = deleteRule);
  $('addGarageRule').disabled = rules.length >= 8;
  $('addGarageRule').onclick = addRule;
}

function ruleRow(rule, index) {
  const triggerOptions = Object.values(runtime.graphCards).map(card => `<option value="${escapeHtml(card.id)}" ${card.id === rule.trigger ? 'selected' : ''}>${escapeHtml(card.name)}</option>`).join('');
  const card = runtime.graphCards[rule.trigger] || Object.values(runtime.graphCards)[0] || {};
  const qualifiers = ['', ...((card.tactical_events || []).map(event => event.tag || event))];
  const actions = [...new Set(Object.values(runtime.graphCards).flatMap(card => card.counters || []))];
  return `<div class="rule-row" data-rule-index="${index}">
    <span class="label">When</span>
    <select data-rule-field="trigger">${triggerOptions}</select>
    <span class="label">And</span>
    <select data-rule-field="qualifier">${qualifiers.map(item => `<option value="${escapeHtml(item)}" ${item === (rule.qualifier || '') ? 'selected' : ''}>${item ? escapeHtml(label(item)) : 'Any event'}</option>`).join('')}</select>
    <span class="label">Then</span>
    <select data-rule-field="action">${actions.map(item => `<option value="${escapeHtml(item)}" ${item === rule.action ? 'selected' : ''}>${escapeHtml(label(item))}</option>`).join('')}</select>
    <button type="button" class="icon-step" data-rule-move="up" aria-label="Move rule up">↑</button>
    <button type="button" class="icon-step" data-rule-move="down" aria-label="Move rule down">↓</button>
    <button type="button" class="icon-step" data-rule-delete aria-label="Delete rule">×</button>
  </div>`;
}

function firstRule() {
  const card = Object.values(runtime.graphCards)[0] || {};
  return { trigger: card.id || '', qualifier: '', action: (card.counters || [])[0] || '' };
}

function addRule() {
  const rules = CBState.get().garageRules || [];
  if (rules.length >= 8) return;
  CBState.set({ garageRules: [...rules, firstRule()] });
  renderGaragePage(CBRouter.current().params);
}

function updateRule(event) {
  const index = Number(event.target.closest('[data-rule-index]').dataset.ruleIndex);
  const rules = structuredClone(CBState.get().garageRules || []);
  rules[index][event.target.dataset.ruleField] = event.target.value;
  if (event.target.dataset.ruleField === 'trigger') {
    const card = runtime.graphCards[event.target.value] || {};
    rules[index].qualifier = '';
    rules[index].action = (card.counters || [])[0] || rules[index].action || '';
  }
  CBState.set({ garageRules: rules });
  renderGaragePage(CBRouter.current().params);
}

function moveRule(event) {
  const index = Number(event.target.closest('[data-rule-index]').dataset.ruleIndex);
  const direction = event.target.dataset.ruleMove === 'up' ? -1 : 1;
  const rules = structuredClone(CBState.get().garageRules || []);
  const nextIndex = index + direction;
  if (nextIndex < 0 || nextIndex >= rules.length) return;
  [rules[index], rules[nextIndex]] = [rules[nextIndex], rules[index]];
  CBState.set({ garageRules: rules });
  renderGaragePage(CBRouter.current().params);
}

function deleteRule(event) {
  const index = Number(event.target.closest('[data-rule-index]').dataset.ruleIndex);
  CBState.set({ garageRules: (CBState.get().garageRules || []).filter((_, i) => i !== index) });
  renderGaragePage(CBRouter.current().params);
}

function renderGarageActions() {
  const button = $('testDriveButton');
  const valid = garageIsValid();
  button.disabled = true;
  button.title = valid ? 'Local script execution is unavailable from a static browser host.' : 'Add one valid rule and fix validation errors first.';
  button.classList.toggle('ready', valid);
}

function garageIsValid() {
  const tier = CBState.get().garageTier;
  const keys = Object.values(garageControlSections).flat().filter(key => tier !== 'remote_endpoint' || garageControlSections.identity.includes(key));
  const controlsValid = keys.every(key => !validateGarageControl(key, garageControlValue(key)));
  const rulesValid = (CBState.get().garageRules || []).some(rule => rule.trigger && rule.action);
  return controlsValid && rulesValid;
}

function renderGarageDrafts() {
  const drafts = loadGarageDrafts();
  CBState.set({ garageDrafts: drafts });
  $('garageDraftName').value = CBState.get().garageDraftName;
  $('garageDraftName').oninput = event => CBState.set({ garageDraftName: event.target.value || 'coachbench-draft' });
  $('saveGarageDraft').onclick = saveGarageDraft;
  $('garageDrafts').innerHTML = drafts.length
    ? drafts.map(draft => `<div class="draft-row"><span>${escapeHtml(draft.name)}</span><button type="button" data-draft-load="${escapeHtml(draft.name)}">Load</button><button type="button" data-draft-delete="${escapeHtml(draft.name)}">Delete</button></div>`).join('')
    : '<p class="muted compact">No saved drafts in this browser.</p>';
  $('garageDrafts').querySelectorAll('[data-draft-load]').forEach(button => button.onclick = loadGarageDraft);
  $('garageDrafts').querySelectorAll('[data-draft-delete]').forEach(button => button.onclick = deleteGarageDraft);
}

function saveGarageDraft() {
  const name = (CBState.get().garageDraftName || 'coachbench-draft').replace(/[^a-z0-9_-]/gi, '-').toLowerCase();
  const payload = { name, garageState: CBState.get().garageState, garageTier: CBState.get().garageTier, garageRules: CBState.get().garageRules || [] };
  try { localStorage.setItem(`${garageDraftPrefix}${name}`, JSON.stringify(payload)); } catch {}
  CBState.set({ garageDraftName: name });
  renderGaragePage(CBRouter.current().params);
}

function loadGarageDrafts() {
  try {
    return Object.keys(localStorage)
      .filter(key => key.startsWith(garageDraftPrefix))
      .map(key => JSON.parse(localStorage.getItem(key)))
      .sort((a, b) => a.name.localeCompare(b.name));
  } catch {
    return [];
  }
}

function loadGarageDraft(event) {
  const draft = loadGarageDrafts().find(item => item.name === event.target.dataset.draftLoad);
  if (!draft) return;
  CBState.set({ garageState: draft.garageState, garageTier: draft.garageTier, garageRules: draft.garageRules || [], garageDraftName: draft.name });
  renderGaragePage(CBRouter.current().params);
}

function deleteGarageDraft(event) {
  const name = event.target.dataset.draftDelete;
  if (!confirm(`Delete ${name}?`)) return;
  try { localStorage.removeItem(`${garageDraftPrefix}${name}`); } catch {}
  renderGaragePage(CBRouter.current().params);
}

async function renderDailySlate() {
  const target = $('dailySlate');
  try {
    const slate = await fetchJson('../data/daily_slate/sample_slate.json');
    const results = await fetchJson('../data/daily_slate/results.json').catch(() => ({ results: [] }));
    target.innerHTML = `<div class="slate-grid">${(slate.entries || []).map((entry, i) => slateCard(entry, i, results.results || [])).join('')}</div>`;
  } catch {
    target.innerHTML = `<p class="muted">${CBEmptyStates.emptySlate()}</p>`;
  }
}

function slateCard(entry, index, results) {
  const match = entry.matchup || {};
  const result = results[index];
  return `<div class="slate-card">
    <strong class="slate-seed">${entry.seed || `Entry ${index + 1}`}</strong>
    <span class="slate-matchup">${label(match.offense)} vs ${label(match.defense)}</span>
    <div class="slate-result"><span class="slate-label">Result</span><span class="slate-value">${result ? label(result.result) : 'Preview Pending'}</span></div>
    <div class="slate-points"><span class="slate-label">Points</span><span class="slate-value">${result ? result.points : '-'}</span></div>
    <p class="slate-note">preview not available in static proof</p>
  </div>`;
}

function renderRosterStrengths() {
  const replay = currentReplay();
  const rosters = replay.agent_garage_config?.rosters;
  if (!rosters) {
    $('rosterStrengths').innerHTML = '<p class="muted">No roster applied - running on neutral baseline.</p>';
    return;
  }
  $('rosterStrengths').innerHTML = `<div class="roster-grid">${rosterSide('Offense', rosters.offense)}${rosterSide('Defense', rosters.defense)}</div>`;
}

function rosterSide(title, roster) {
  if (!roster) return `<div class="roster-side"><h3>${title}</h3><p class="muted">No roster applied.</p></div>`;
  const entries = Object.entries(roster.values || {}).sort((a, b) => b[1] - a[1]);
  const strengths = new Set(entries.slice(0, 3).map(([key]) => key));
  const weaknesses = new Set(entries.slice(-3).map(([key]) => key));
  return `<div class="roster-side">
    <h3>${title}</h3>
    <p class="muted compact">${roster.label || roster.roster_id} · Budget: ${roster.budget_points || 0} / 600</p>
    ${entries.map(([key, raw]) => {
      const value = Number(raw || 0);
      const bucket = strengths.has(key) ? 'Strength' : weaknesses.has(key) ? 'Weakness' : 'Neutral';
      return `<div class="roster-bar ${bucket === 'Strength' ? 'roster-strength' : bucket === 'Weakness' ? 'roster-weakness' : ''}">
        <label><span>${label(key)}</span><strong>${value}</strong></label>
        <div class="meter"><div class="fill" style="width:${value}%"></div></div>
        <small>${bucket}</small>
      </div>`;
    }).join('')}
  </div>`;
}

function setupOverlay() {
  $('openGraphExplorer').onclick = openGraphExplorer;
  $('closeGraphExplorer').onclick = closeGraphExplorer;
  $('overlayBackdrop').onclick = closeGraphExplorer;
  $('graphSearch').oninput = renderGraphExplorer;
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closeGraphExplorer(); });
}

function openGraphExplorer() {
  $('graphOverlay').hidden = false;
  $('graphSearch').value = '';
  renderGraphExplorer();
  $('graphSearch').focus();
}

function closeGraphExplorer() {
  $('graphOverlay').hidden = true;
}

function renderGraphExplorer() {
  const query = ($('graphSearch').value || '').toLowerCase();
  const cards = Object.values(runtime.graphCards).filter(card => JSON.stringify(card).toLowerCase().includes(query));
  $('graphExplorerList').innerHTML = cards.map(card => graphCardHtml(card, card.id)).join('') || '<p class="muted">No matching graph cards.</p>';
}

function morphText(el, next) {
  if (el.textContent === next) return;
  el.style.opacity = '0';
  setTimeout(() => { el.textContent = next; el.style.opacity = '1'; }, motionMs('--motion-outcome'));
}

function flashScore(kind) {
  const card = $('scorecard');
  card.classList.remove('flash-good', 'flash-warn');
  void card.offsetWidth;
  card.classList.add(kind === 'good' ? 'flash-good' : 'flash-warn');
}

function createAutoplay({ count, intervalMs, onTick, onStateChange }) {
  let timer = null;
  let running = false;
  const state = () => onStateChange?.(running);
  const start = () => {
    if (reduced() || running || count < 2 || intervalMs <= 0) return;
    running = true;
    CBState.set({ autoplay: true });
    state();
    timer = setInterval(() => onTick((CBState.get().selectedIndex + 1) % count), intervalMs);
  };
  const stop = () => {
    if (timer) clearInterval(timer);
    timer = null;
    running = false;
    CBState.set({ autoplay: false });
    state();
  };
  return { start, stop, toggle: () => running ? stop() : start(), isRunning: () => running, dispose: stop };
}

function autoplayIntervalMs() {
  return motionMs('--autoplay-interval');
}

function setupFeedAutoplay() {
  const replay = currentReplay();
  runtime.auto?.dispose();
  runtime.auto = createAutoplay({
    count: replay.plays.length,
    intervalMs: autoplayIntervalMs(),
    onTick: i => selectPlay(i, { syncHash: true, scroll: true, source: 'autoplay' }),
    onStateChange: updatePlayPauseButton,
  });
  $('resumeFeed').onclick = () => runtime.auto.start();
}

function updatePlayPauseButton(running) {
  const button = $('resumeFeed');
  const progress = $('autoplayProgress');
  button.hidden = running || reduced();
  button.textContent = 'Resume';
  button.setAttribute('aria-label', 'Resume autoplay');
  progress.classList.remove('running');
  void progress.offsetWidth;
  if (running && !reduced()) progress.classList.add('running');
}

function pauseForUser() {
  runtime.auto?.stop();
  if (!reduced()) $('resumeFeed').hidden = false;
}

function restartAutoplayProgress() {
  if (!runtime.auto?.isRunning()) return;
  const progress = $('autoplayProgress');
  progress.classList.remove('running');
  void progress.offsetWidth;
  if (!reduced()) progress.classList.add('running');
}

function mountRows(root) {
  root.querySelectorAll ? root.querySelectorAll('.row-mount, .panel').forEach(panel => {
    panel.classList.remove('mount');
    [...panel.children].slice(0, 6).forEach(child => child.style.animationDelay = 'var(--motion-card-swap)');
    void panel.offsetWidth;
    panel.classList.add('mount');
  }) : null;
}

function normalizeReplayPageRoute() {
  if (!location.pathname.endsWith('/replay.html')) return;
  if (CBRouter.current().name !== 'replays') return;
  const seed = new URLSearchParams(location.search).get('seed');
  CBRouter.go('replay-detail', { id: seed ? `seed-${seed}` : 'seed-42' });
}

syncMotionPreference();
if (typeof motionQuery.addEventListener === 'function') {
  motionQuery.addEventListener('change', syncMotionPreference);
} else if (typeof motionQuery.addListener === 'function') {
  motionQuery.addListener(syncMotionPreference);
}
normalizeReplayPageRoute();
CBRouter.subscribe(route => handleRoute(route).catch(error => {
  document.body.innerHTML = `<pre>Failed to load route: ${error}</pre>`;
}));
handleRoute(CBRouter.current()).catch(error => {
  document.body.innerHTML = `<pre>Failed to load route: ${error}</pre>`;
});
