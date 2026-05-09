const runtime = { graphCards: {}, conceptLabels: {}, profiles: {}, parameterGlossary: {}, garageRunnerIndex: null, auto: null, autoScrolling: false, skipNextRouteScroll: false, sharedLoaded: false, replayIndex: null, replaySources: {}, replayId: null, activeRunRecordId: null, manifest: null };
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
  identity: ['offensive_archetype', 'defensive_archetype', 'runner_seed'],
  strategy: [],
  resource: [],
};
const numericControls = new Set(['adaptation_speed', 'screen_trigger_confidence', 'explosive_shot_tolerance', 'disguise_sensitivity', 'pressure_frequency', 'counter_repeat_tolerance']);
const offenseParameterOrder = ['risk_tolerance', 'adaptation_speed', 'screen_trigger_confidence', 'explosive_shot_tolerance', 'run_pass_tendency'];
const defenseParameterOrder = ['risk_tolerance', 'disguise_sensitivity', 'pressure_frequency', 'counter_repeat_tolerance'];
const riskOrder = ['low', 'medium_low', 'medium', 'medium_high', 'high'];
const CHIP_CARD_CONCEPT = {
  'redzone.bunch_mesh_vs_match.v1': 'bunch_mesh',
  'redzone.screen_vs_zero_pressure.v1': 'screen',
  'redzone.screen_vs_simulated_pressure.v1': 'screen',
  'redzone.outside_zone_vs_bear.v1': 'bear_front',
  'redzone.play_action_after_run_tendency.v1': 'play_action_flood',
  'redzone.vertical_vs_two_high.v1': 'two_high_shell',
  'redzone.quick_game_vs_two_high.v1': 'quick_game',
  'redzone.rpo_vs_static_zone.v1': 'rpo_glance',
};
const garageDraftPrefix = 'coachbench.garageDraft.';
const garageActiveDraftKey = 'coachbench.garageActiveDraft';
const garageRecentRunsKey = 'coachbench.garageRecentRuns';
const garageRecentLimit = 10;
const motionQuery = typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
const reduced = () => typeof document !== 'undefined' && document.documentElement.classList.contains('reduced-motion');
const label = key => runtime.conceptLabels[key] || String(key || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const value = item => item === null || item === undefined || item === '' ? '-' : item;
const pct = raw => Math.round(Number(raw || 0) * 100);
const currentReplay = () => CBState.get().replay;
const escapeHtml = raw => String(raw ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const truncate = (raw, max = 64) => String(raw || '').length > max ? `${String(raw).slice(0, max - 1)}…` : String(raw || '');
const toHandle = raw => {
  if (!raw) return '';
  const cleaned = String(raw).toLowerCase().replace(/[^a-z0-9]/g, '');
  return cleaned.length > 16 ? cleaned.slice(0, 16) : cleaned;
};
const displayHandle = raw => {
  const handle = toHandle(raw);
  return handle.replace(/^team[ab]/, '').replace(/^team/, '') || handle;
};
const launchName = (raw, fallback) => {
  const text = String(raw || '').trim();
  return /team\s+[ab]|static\s+(baseline|offense|defense)|adaptive\s+(counter|offense|defense)/i.test(text)
    ? fallback
    : (text || fallback);
};
const chipConceptFor = id => CHIP_CARD_CONCEPT[String(id || '').toLowerCase()] || String(id || '').toLowerCase();
const chipClassFor = id => window.CBChips?.chipClassFor(chipConceptFor(id)) || 'chip';
const formatMatchup = raw => {
  const parts = String(raw || '').split(/\s*(?:vs|⇌|⇄|—|–|-)\s*/i).filter(Boolean);
  if (parts.length < 2) return toHandle(raw);
  return `${toHandle(parts[0])} ⇌ ${toHandle(parts[1])}`;
};
const terminalClass = terminal => {
  const value = String(terminal || '').toLowerCase();
  return value === 'touchdown' || value === 'stopped' ? value : '';
};

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} ${response.status}`);
  return response.json();
}

async function loadReplayIndex() {
  if (runtime.replayIndex) return runtime.replayIndex;
  const index = await fetchJson('replay_index.json').catch(() => []);
  const manifest = await loadManifest().catch(() => ({ replays: [] }));
  const manifestBySeed = new Map((manifest.replays || []).map(item => [String(item.seed), item]));
  runtime.replayIndex = Array.isArray(index) ? index.map(item => {
    const launch = manifestBySeed.get(String(item.seed));
    return launch ? {
      ...item,
      offense_label: launch.offense_label,
      defense_label: launch.defense_label,
      offense_identity_id: launch.offense_identity_id,
      defense_identity_id: launch.defense_identity_id,
      technical_label: launch.technical_label,
      path: launch.replay_path || item.path,
      plays: launch.summary?.plays ?? item.plays,
      top_concept: launch.summary?.top_concept || item.top_concept,
      terminal_result: launch.summary?.result || item.terminal_result,
      points: launch.summary?.points ?? item.points,
      invalid_actions: launch.summary?.invalid_action_count ?? item.invalid_actions,
    } : item;
  }) : [];
  runtime.replaySources = {
    ...fallbackReplaySources,
    ...Object.fromEntries(runtime.replayIndex.map(item => [item.id, item.path])),
  };
  await loadGarageRunnerIndex();
  mergeGarageRunnerSources();
  return runtime.replayIndex;
}

async function loadGarageRunnerIndex() {
  if (runtime.garageRunnerIndex) return runtime.garageRunnerIndex;
  runtime.garageRunnerIndex = await fetchJson('../data/garage_runner/index.json').catch(() => ({ entries: [], seed_pack: [] }));
  mergeGarageRunnerSources();
  return runtime.garageRunnerIndex;
}

function garageRunnerEntries() {
  return runtime.garageRunnerIndex?.entries || [];
}

function mergeGarageRunnerSources() {
  const entries = garageRunnerEntries();
  if (!entries.length) return;
  runtime.replaySources = {
    ...runtime.replaySources,
    ...Object.fromEntries(entries.map(item => [item.id, item.path])),
  };
}

async function loadManifest() {
  if (runtime.manifest) return runtime.manifest;
  runtime.manifest = await fetchJson('showcase_manifest.json').catch(() => ({ replays: [] }));
  return runtime.manifest;
}

async function loadSharedData() {
  if (runtime.sharedLoaded) return;
  const [graph, concepts, loadedProfiles, glossary, runnerIndex] = await Promise.all([
    fetchJson('../graph/redzone_v0/interactions.json').catch(() => ({ interactions: [] })),
    fetchJson('../graph/redzone_v0/concepts.json').catch(() => ({ offense: [], defense: [] })),
    fetchJson('../agent_garage/profiles.json').catch(() => ({})),
    fetchJson('../agent_garage/parameter_glossary.json').catch(() => ({})),
    fetchJson('../data/garage_runner/index.json').catch(() => ({ entries: [], seed_pack: [] })),
  ]);
  runtime.graphCards = Object.fromEntries((graph.interactions || []).map(card => [card.id, card]));
  runtime.conceptLabels = {};
  [...(concepts.offense || []), ...(concepts.defense || [])].forEach(item => runtime.conceptLabels[item.id] = item.label || item.name);
  runtime.profiles = loadedProfiles;
  runtime.parameterGlossary = glossary;
  runtime.garageRunnerIndex = runnerIndex;
  mergeGarageRunnerSources();
  runtime.sharedLoaded = true;
}

function replaySourceForId(id) {
  return runtime.replaySources[id] || fallbackReplaySources[id] || showcaseReplaySource(id);
}

async function fetchReplayById(id) {
  await loadSharedData();
  await loadReplayIndex();
  await loadManifest();
  const source = replaySourceForId(id);
  if (!source) {
    const apiReplay = await fetchJson(`/v1/replays/${encodeURIComponent(id)}`).catch(() => null);
    if (apiReplay) return annotateReplay(apiReplay);
    throw new Error(`Replay not found: ${id}`);
  }
  const rawReplay = await fetchJson(source).catch(error => {
    if (id === 'seed-42') return fetchJson(fallbackReplaySources['static-proof']);
    throw error;
  });
  return annotateReplay(rawReplay);
}

async function loadReplay(id, playParam) {
  await loadSharedData();
  await loadReplayIndex();
  await loadManifest();
  const replay = await fetchReplayById(id).catch(() => null);
  if (!replay) return renderReplayNotFound(id);
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
  $('replayNotFound').innerHTML = `<div class="panel"><h1>Replay not found</h1><p class="subhead">${CBEmptyStates.notFoundReplay(id)}</p><a class="btn btn--primary" href="#/replays">Back to replays</a></div>`;
}

function renderAll() {
  renderHeader();
  renderCompactAgentCard();
  renderDailySlate();
  renderRosterStrengths();
  renderPlayFeed();
  renderDriveSummary();
  renderFilmRoom();
  renderBeforeAfter();
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
  const drawer = $('rightDrawer');
  const scrim = $('rightDrawerScrim');
  const drawerOpen = route.name === 'replay-detail';
  if (drawer) drawer.hidden = !drawerOpen;
  if (scrim) scrim.hidden = !drawerOpen;
  document.body.classList.toggle('right-drawer-open', drawerOpen);
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
    runtime.activeRunRecordId = route.params.run || null;
    if (runtime.replayId === route.params.id && currentReplay()) {
      const shouldScroll = !runtime.skipNextRouteScroll;
      runtime.skipNextRouteScroll = false;
      selectPlay(playToIndex(route.params.play, currentReplay().plays.length), { syncHash: false, scroll: shouldScroll, source: 'route' });
      renderBeforeAfter();
    } else {
      await loadReplay(route.params.id, route.params.play);
    }
  } else if (route.name === 'garage') {
    renderRouteStub('garageRouteCopy', 'Saved drafts load from the local backend. Assistant editing lands next.');
  } else if (route.name === 'reports') {
    renderReports(route.params.compare);
  } else if (route.name === 'arena') {
    renderRouteStub('arenaRouteCopy', 'Run Best-of-N, gauntlets, and tournaments from saved drafts through the local backend.');
  }
  window.CBLeftRail?.updateRouteCopy?.(route);
  renderCompareTray();
}

async function renderGallery() {
  ensureReplayGalleryShell();
  const target = $('replayGallery');
  if (!target) return;
  await loadSharedData();
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
  window.CBLeftRail?.bindReplayButtons?.(target);
  mountRows(target);
}

function renderRouteStub(id, copy) {
  $(id).textContent = copy;
}

function renderReports(compare) {
  const ids = String(compare || '').split(',').filter(Boolean);
  renderRouteStub('reportsRouteCopy', ids.length ? `Reserved comparison: ${ids.join(', ')}.` : 'Open an Arena report or pin replays to compare fixed-seed outcomes.');
}

function renderReplayCard(item) {
  const pinned = CBState.get().pinnedForCompare.includes(item.id);
  const seed = item.id === 'static-proof' ? 'STATIC PROOF' : `SEED ${item.seed}`;
  const terminal = terminalClass(item.terminal_result);
  const offenseLabel = launchName(item.offense_label, item.technical_label?.offense || 'Offense');
  const defenseLabel = launchName(item.defense_label, item.technical_label?.defense || 'Defense');
  const matchup = `${offenseLabel} ⇌ ${defenseLabel}`;
  const points = item.points ?? item.summary?.points;
  const resultText = [label(item.terminal_result || 'result'), points === undefined ? null : `${points} pts`].filter(Boolean).join(' · ');
  const conceptChips = galleryConceptChips(item, 3);
  return `<article class="replay-card panel" data-gallery-card="${escapeHtml(item.id)}">
    <button class="compare-toggle" type="button" data-compare-id="${escapeHtml(item.id)}" aria-pressed="${pinned}">${pinned ? 'Pinned' : '+ Compare'}</button>
    <a class="replay-card-main" href="#/replays/${encodeURIComponent(item.id)}">
      <span class="eyebrow" data-card-field="eyebrow"><span class="seed-dot ${terminal ? `seed-dot--${terminal}` : ''}"></span>${seed} · RED ZONE · ${item.plays} PLAYS</span>
      <strong data-card-field="matchup">${escapeHtml(matchup)}</strong>
      <span class="result-row" data-card-field="result"><span>${escapeHtml(resultText)}</span><em>${escapeHtml(label(item.terminal_result))}</em></span>
      <span class="identity-row"><span class="identity-chip identity-chip--offense">${escapeHtml(offenseLabel)}</span><span class="identity-chip identity-chip--defense">${escapeHtml(defenseLabel)}</span></span>
      ${conceptChips ? `<span class="gallery-concepts">${conceptChips}</span>` : ''}
      ${gallerySparkline(item.sparkline || [], item.terminal_result)}
      <span class="metric-row"><span data-card-field="invalid_actions">${item.invalid_actions} invalid actions</span><span data-card-field="top_graph_event">${escapeHtml(truncate(item.top_graph_event))}</span></span>
    </a>
  </article>`;
}

function ensureReplayGalleryShell() {
  const route = document.querySelector('[data-route="replays"]');
  if (!route || route.dataset.galleryShell === 'ready') return;
  const gallery = $('replayGallery') || document.createElement('div');
  gallery.id = 'replayGallery';
  gallery.className = 'replay-gallery';
  route.innerHTML = '<header class="gallery-header"><h2>All replays</h2><p class="muted">Browse every seeded run. Pin two or more to compare.</p></header>';
  route.appendChild(gallery);
  route.dataset.galleryShell = 'ready';
}

function galleryConceptChips(item, coloredBudget) {
  return galleryConceptIds(item).slice(0, 6).map((id, index) => {
    const klass = index < coloredBudget ? chipClassFor(id) : 'chip';
    return `<span class="${klass}" title="${escapeHtml(id)}">${escapeHtml(galleryChipLabel(id))}</span>`;
  }).join('');
}

function galleryConceptIds(item) {
  const ids = [];
  if (item.top_concept) ids.push(item.top_concept);
  const eventText = String(item.top_graph_event || '').toLowerCase();
  if (eventText) {
    const match = Object.values(runtime.graphCards).find(card => String(card.name || '').toLowerCase() === eventText);
    if (match) ids.push(chipConceptFor(match.id));
  }
  return [...new Set(ids.filter(Boolean))];
}

function galleryChipLabel(id) {
  const conceptId = chipConceptFor(id);
  return runtime.conceptLabels[conceptId] || label(conceptId);
}

function gallerySparkline(values, terminal) {
  const status = terminalClass(terminal);
  const klass = status === 'touchdown' ? 'gallery-sparkline gallery-sparkline--positive'
    : status === 'stopped' ? 'gallery-sparkline gallery-sparkline--negative'
      : 'gallery-sparkline';
  const nums = values.length ? values.map(Number) : [0];
  const min = Math.min(...nums), max = Math.max(...nums), range = max - min || 1;
  const x = i => nums.length === 1 ? 4 : 4 + (i / (nums.length - 1)) * 88;
  const y = raw => 20 - ((raw - min) / range) * 16;
  const points = nums.map((raw, i) => `${x(i).toFixed(2)},${y(raw).toFixed(2)}`).join(' ');
  return `<svg class="${klass}" width="96" height="24" viewBox="0 0 96 24" aria-hidden="true" data-card-field="sparkline"><path class="gallery-spark-line" d="M${points.replaceAll(' ', ' L')}"></path></svg>`;
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
  renderReplayHero(replay);
  $('modeBanner').textContent = staticMode
    ? 'Static schema proof replay'
    : 'Engine-generated replay';
  $('modeBanner').classList.toggle('static-proof', staticMode);
  morphText($('resultLabel'), label(replay.score.result));
  morphText($('pointsLabel'), `${replay.score.points} pts`);
  $('episodeLabel').textContent = replay.metadata.episode_id;
  if (replay.score.result === 'touchdown') flashScore('good');
  if (replay.score.result === 'stopped') flashScore('warn');
}

function renderReplayHero(replay) {
  const seed = new URLSearchParams(window.location.search).get('seed')
    || String(runtime.replayId || '').match(/^seed-(\d+)$/)?.[1]
    || replay.agent_garage_config?.runner_seed;
  const meta = (runtime.manifest?.replays || []).find(item => String(item.seed) === String(seed));
  const offenseHandle = meta?.offense_label || launchName(replay.agents?.offense, 'Offense');
  const defenseHandle = meta?.defense_label || launchName(replay.agents?.defense, 'Defense');
  const matchup = $('replayHeroMatchup');
  const metaLine = $('replayHeroMeta');
  if (matchup) matchup.textContent = `${offenseHandle || 'Offense'} ⇌ ${defenseHandle || 'Defense'}`;
  const drawerTitle = $('drawerTitle');
  if (drawerTitle) drawerTitle.textContent = `${offenseHandle || 'Offense'} ⇌ ${defenseHandle || 'Defense'}`;
  if (metaLine) {
    metaLine.innerHTML = `SEED ${seed ?? '—'}<span class="dot"></span>${replay.plays.length} plays<span class="dot"></span>${label(replay.score.result)}<span class="dot"></span>${replay.score.points} pts`;
  }
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
  feed.querySelectorAll('.feed-card[data-feed-index]').forEach(card => {
    card.onclick = () => {
      pauseForUser();
      selectPlay(Number(card.dataset.feedIndex), { syncHash: true, scroll: false, source: 'click' });
    };
  });
  feed.querySelectorAll('[data-assistant-play]').forEach(button => {
    button.onclick = event => {
      event.stopPropagation();
      const playIndex = Number(button.dataset.assistantPlay);
      window.dispatchEvent(new CustomEvent('coachbench:assistant:request', {
        detail: { type: 'film_room_tweak', run_id: runtime.replayId || 'seed-42', play_index: playIndex },
      }));
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
  const turningPoint = currentReplay().film_room?.turning_point?.play_index === pub.play_index;
  const adaptation = play.is_adaptation;
  const cards = (pub.graph_card_ids || []).map(id => `<span class="${graphChipClass(id, adaptation)}" title="${escapeHtml(id)}">${escapeHtml(cardLabel(id))}</span>`).join('');
  return `<article class="feed-card-shell" role="listitem">
    <button class="feed-card ${adaptation ? 'is-adaptation' : ''}" type="button" data-feed-index="${index}" aria-current="false">
      <span class="feed-eyebrow">${adaptation ? `ADAPTATION · PLAY ${pub.play_index}` : `PLAY ${pub.play_index} · ${offense} vs ${defense}`}${turningPoint ? ' · ★ TURNING POINT' : ''}</span>
      <span class="feed-body">${outcome}</span>
      ${adaptation ? `<span class="feed-causal">${causalLine(play)}</span>` : ''}
      <span class="feed-tags">${cards || '<span class="muted">No graph card</span>'}</span>
    </button>
    <button class="feed-tweak-action ghost-button" type="button" data-assistant-play="${pub.play_index}">Apply suggested tweak</button>
  </article>`;
}

function graphChipClass(cardId, isAdaptation) {
  return chipClassFor(cardId);
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
  const ball = $('ball');
  if (typeof window !== 'undefined' && window.CBField) return window.CBField.positionBall(ball, yardline, terminalReason, reduced());
  const clamped = Math.max(0, Math.min(25, Number(yardline)));
  ball.style.left = `${8 + ((25 - clamped) / 25) * 84}%`;
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
  const W = 720, H = 180;
  const padL = 36, padR = 32, padT = 28, padB = 28;
  const min = Math.min(...values), max = Math.max(...values), range = max - min || 1;
  const x = i => padL + (i / Math.max(1, values.length - 1)) * (W - padL - padR);
  const y = v => H - padB - ((v - min) / range) * (H - padT - padB);
  const pts = values.map((v, i) => `${x(i).toFixed(2)},${y(v).toFixed(2)}`).join(' ');
  const zeroY = (min <= 0 && max >= 0 ? y(0) : y(min)).toFixed(2);
  const bestIndex = values.reduce((winner, v, i) => Math.abs(v) > Math.abs(values[winner]) ? i : winner, 0);
  const bestValue = values[bestIndex];
  const ticks = values.map((_, i) => `<text class="spark-tick" x="${x(i).toFixed(2)}" y="${(H - padB + 18).toFixed(2)}" text-anchor="middle">${i + 1}</text>`).join('');
  return `<div class="sparkline-wrap"><svg class="sparkline" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Expected-value delta per play">
    <text class="spark-label" x="${padL}" y="20">EP delta</text>
    <line class="spark-axis" x1="${padL}" x2="${W - padR}" y1="${zeroY}" y2="${zeroY}"></line>
    <path class="draw-on-mount" d="M${pts.replaceAll(' ', ' L')}" />
    <circle class="spark-dot" cx="${x(bestIndex).toFixed(2)}" cy="${y(bestValue).toFixed(2)}" r="4"></circle>
    <text class="spark-dot-label" x="${Math.min(W - padR - 4, x(bestIndex) + 8).toFixed(2)}" y="${Math.max(14, y(bestValue) - 8).toFixed(2)}">${bestValue >= 0 ? '+' : ''}${bestValue.toFixed(2)}</text>
    ${ticks}
  </svg></div>`;
}

function renderFilmRoom() {
  const replay = currentReplay();
  const target = $('filmRoom');
  target.innerHTML = renderFilmRoomHtml(replay);
  target.querySelectorAll('[data-apply-tweak]').forEach(button => {
    button.onclick = () => dispatchAssistantRequest({
      type: 'film_room_tweak',
      run_id: runtime.replayId || 'seed-42',
      tweak_id: button.dataset.applyTweak,
      play_index: replay.film_room?.turning_point?.play_index || CBState.get().selectedIndex + 1,
    });
  });
  target.querySelectorAll('[data-tune-agent]').forEach(button => {
    button.onclick = () => dispatchAssistantRequest({ type: 'film_room_tweak', run_id: runtime.replayId || 'seed-42', play_index: CBState.get().selectedIndex + 1 });
  });
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
  const tweakChips = renderFilmRoomTweakChips(replay);
  return `<section class="film-compressed">
    <div class="film-actions">
      <button class="ghost-button" type="button" data-tune-agent>Tune Agent</button>
    </div>
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
    ${tweakChips}
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

function filmRoomTweaks(replay) {
  return replay?.film_room_tweaks || replay?.film_room?.film_room_tweaks || [];
}

function renderFilmRoomTweakChips(replay) {
  const tweaks = filmRoomTweaks(replay);
  if (!tweaks.length) return '';
  return `<div class="film-tweak-list">
    ${tweaks.map(tweak => `<article class="film-tweak-chip">
      <div>
        <strong>${escapeHtml(label(tweak.parameter))}</strong>
        <span>${escapeHtml(tweak.rationale?.rendered || 'Structured tweak available.')}</span>
      </div>
      <button class="ghost-button" type="button" data-apply-tweak="${escapeHtml(tweak.tweak_id)}">Apply suggested tweak</button>
    </article>`).join('')}
  </div>`;
}

function garageUrl(params = {}) {
  const query = new URLSearchParams();
  if (params.from) query.set('from', params.from);
  if (params.apply) query.set('apply', params.apply);
  const text = query.toString();
  return `garage.html${text ? `?${text}` : ''}`;
}

function navigateToGarage(params = {}) {
  window.location.href = garageUrl(params);
}

function dispatchAssistantRequest(detail) {
  window.dispatchEvent(new CustomEvent('coachbench:assistant:request', { detail }));
}

async function renderBeforeAfter() {
  const target = $('beforeAfterPanel');
  if (!target) return;
  const replay = currentReplay();
  const runs = loadGarageRecentRuns();
  const currentRun = runs.find(run => run.run_record_id && run.run_record_id === runtime.activeRunRecordId)
    || runs.find(run => run.id === runtime.replayId && run.applied_tweak);
  const applied = currentRun?.applied_tweak;
  if (!replay || !applied?.parameter || !currentRun.parent_run_id) {
    target.hidden = true;
    target.innerHTML = '';
    return;
  }
  target.hidden = false;
  target.innerHTML = `<h2>Before / After</h2><p class="muted compact">Loading scoped comparison for ${escapeHtml(label(applied.parameter))}.</p>`;
  const replayId = runtime.replayId;
  const parentReplay = await fetchReplayById(currentRun.parent_run_id).catch(() => null);
  if (runtime.replayId !== replayId) return;
  if (!parentReplay) {
    target.innerHTML = `<h2>Before / After</h2><p class="muted compact">No scoped comparison is available because the parent run could not be loaded.</p>`;
    return;
  }
  const signals = beforeAfterSignalsFor(applied.parameter);
  if (!signals.length) {
    target.innerHTML = `<h2>Before / After</h2><p class="muted compact">No scoped comparison is available for ${escapeHtml(label(applied.parameter))}.</p>`;
    return;
  }
  const rows = signals.map(signal => compareSignal(signal, parentReplay, replay)).filter(Boolean);
  if (!rows.length) {
    target.innerHTML = `<h2>Before / After</h2><p class="muted compact">No scoped comparison is available for ${escapeHtml(label(applied.parameter))}.</p>`;
    return;
  }
  target.innerHTML = `<div class="panel-title">
    <h2>Before / After</h2>
    <span>${escapeHtml(label(applied.parameter))}</span>
  </div>
  <p class="muted compact">Scoped to the applied tweak from ${escapeHtml(currentRun.parent_run_id)}.</p>
  <div class="before-after-grid">
    ${rows.map(row => `<div class="before-after-row">
      <span>${escapeHtml(row.label)}</span>
      <strong>${escapeHtml(row.before)}</strong>
      <strong>${escapeHtml(row.after)}</strong>
      <small>${escapeHtml(row.delta)}</small>
    </div>`).join('')}
  </div>`;
}

function beforeAfterSignalsFor(parameter) {
  const required = {
    screen_trigger_confidence: ['screen_call_count', 'screen_graph_events', 'pressure_screen_belief_trajectory'],
    adaptation_speed: ['time_to_first_counter', 'belief_delta_magnitudes'],
  };
  return required[parameter] || runtime.parameterGlossary[parameter]?.before_after_signals || [];
}

function uniqueReplayEvents(replay) {
  const seen = new Set();
  return (replay?.plays || []).flatMap(play => {
    const playIndex = Number(play.public?.play_index || 0);
    const events = [
      ...(play.public?.events || []),
      ...(play.offense_observed?.events || []),
      ...(play.defense_observed?.events || []),
    ];
    return events.filter(event => {
      const key = `${playIndex}:${event.graph_card_id}:${event.tag}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  });
}

function countOffenseConcepts(replay, concepts) {
  const set = new Set(concepts);
  return (replay?.plays || []).filter(play => set.has(play.public?.offense_action?.concept_family)).length;
}

function countDefenseCalls(replay, calls) {
  const set = new Set(calls);
  return (replay?.plays || []).filter(play => set.has(play.public?.defense_action?.coverage_family)).length;
}

function countEventTags(replay, tags) {
  const set = new Set(tags);
  return uniqueReplayEvents(replay).filter(event => set.has(event.tag)).length;
}

function countRiskCalls(replay, side, riskLevels) {
  const set = new Set(riskLevels);
  const key = side === 'defense' ? 'defense_action' : 'offense_action';
  return (replay?.plays || []).filter(play => set.has(play.public?.[key]?.risk_level)).length;
}

function resourceBurn(replay, side) {
  return (replay?.plays || []).reduce((total, play) => {
    const snapshot = play.public?.resource_budget_snapshot || {};
    return total + Object.values(snapshot[`${side}_cost`] || {}).reduce((sum, raw) => sum + Number(raw || 0), 0);
  }, 0);
}

function firstGraphEventPlay(replay) {
  const plays = replay?.plays || [];
  const found = plays.find(play => uniquePlayEvents(play).length > 0);
  return found ? Number(found.public?.play_index || 0) : null;
}

function uniquePlayEvents(play) {
  const seen = new Set();
  return [
    ...(play.public?.events || []),
    ...(play.offense_observed?.events || []),
    ...(play.defense_observed?.events || []),
  ].filter(event => {
    const key = `${event.graph_card_id}:${event.tag}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function beliefDeltaMagnitude(replay) {
  let total = 0;
  let previous = null;
  (replay?.plays || []).forEach(play => {
    const current = play.offense_observed?.belief_after || {};
    if (previous) {
      Object.keys(current).forEach(key => {
        if (previous[key] !== undefined) total += Math.abs(Number(current[key] || 0) - Number(previous[key] || 0));
      });
    }
    previous = current;
  });
  return Number(total.toFixed(2));
}

function beliefTrajectorySummary(replay, keys) {
  return keys.map(key => {
    const values = (replay?.plays || []).map(play => Number(play.offense_observed?.belief_after?.[key])).filter(Number.isFinite);
    if (!values.length) return `${label(key)} -`;
    return `${label(key)} ${pct(values[0])}%→${pct(values[values.length - 1])}%`;
  }).join(' · ');
}

function compareSignal(signal, before, after) {
  const metric = beforeAfterMetric(signal);
  if (!metric) return null;
  const left = metric.value(before);
  const right = metric.value(after);
  return {
    label: metric.label,
    before: metric.format(left),
    after: metric.format(right),
    delta: metric.delta(left, right),
  };
}

function numericDelta(left, right, suffix = '') {
  const delta = Number(right) - Number(left);
  if (!Number.isFinite(delta)) return '';
  return `${delta >= 0 ? '+' : ''}${delta}${suffix}`;
}

function beforeAfterMetric(signal) {
  const countFormat = raw => `${raw}`;
  const countDelta = (left, right) => numericDelta(left, right);
  const metrics = {
    screen_call_count: {
      label: 'Screen call count',
      value: replay => countOffenseConcepts(replay, ['screen']),
      format: countFormat,
      delta: countDelta,
    },
    screen_graph_events: {
      label: 'Screen graph events',
      value: replay => countEventTags(replay, ['pressure_punished', 'space_created_after_rush', 'screen_baited', 'simulated_pressure_revealed']),
      format: countFormat,
      delta: countDelta,
    },
    pressure_screen_belief_trajectory: {
      label: 'Pressure/screen belief trajectory',
      value: replay => beliefTrajectorySummary(replay, ['true_pressure_confidence', 'screen_trap_risk']),
      format: raw => raw,
      delta: () => 'scoped trace',
    },
    time_to_first_counter: {
      label: 'Time to first graph counter',
      value: firstGraphEventPlay,
      format: raw => raw ? `play ${raw}` : 'none',
      delta: (left, right) => left && right ? numericDelta(left, right, ' plays') : 'changed',
    },
    belief_delta_magnitudes: {
      label: 'Belief delta magnitude',
      value: beliefDeltaMagnitude,
      format: raw => String(raw),
      delta: (left, right) => numericDelta(left, right),
    },
    risk_call_mix: {
      label: 'Aggressive risk calls',
      value: replay => countRiskCalls(replay, 'offense', ['aggressive']) + countRiskCalls(replay, 'defense', ['aggressive']),
      format: countFormat,
      delta: countDelta,
    },
    drive_outcome: {
      label: 'Drive outcome',
      value: replay => `${label(replay.score?.result)} · ${replay.score?.points || 0} pts`,
      format: raw => raw,
      delta: () => 'result',
    },
    explosive_call_count: {
      label: 'Vertical shot calls',
      value: replay => countOffenseConcepts(replay, ['vertical_shot']),
      format: countFormat,
      delta: countDelta,
    },
    explosive_graph_events: {
      label: 'Explosive-shot graph events',
      value: replay => countEventTags(replay, ['explosive_window_capped', 'underneath_space_conceded']),
      format: countFormat,
      delta: countDelta,
    },
    run_pass_mix: {
      label: 'Run/pass mix',
      value: replay => {
        const runs = countOffenseConcepts(replay, ['inside_zone', 'outside_zone', 'power_counter']);
        const passes = (replay.plays || []).length - runs;
        return `${runs} run / ${passes} pass`;
      },
      format: raw => raw,
      delta: () => 'mix',
    },
    play_action_call_count: {
      label: 'Play-action calls',
      value: replay => countOffenseConcepts(replay, ['play_action_flood', 'bootleg']),
      format: countFormat,
      delta: countDelta,
    },
    disguise_call_count: {
      label: 'Disguise calls',
      value: replay => countDefenseCalls(replay, ['simulated_pressure', 'trap_coverage']),
      format: countFormat,
      delta: countDelta,
    },
    disguise_graph_events: {
      label: 'Disguise graph events',
      value: replay => countEventTags(replay, ['screen_baited', 'simulated_pressure_revealed']),
      format: countFormat,
      delta: countDelta,
    },
    pressure_call_count: {
      label: 'Pressure calls',
      value: replay => countDefenseCalls(replay, ['zero_pressure', 'simulated_pressure']),
      format: countFormat,
      delta: countDelta,
    },
    pressure_graph_events: {
      label: 'Pressure graph events',
      value: replay => countEventTags(replay, ['pressure_punished', 'space_created_after_rush', 'screen_baited']),
      format: countFormat,
      delta: countDelta,
    },
    resource_burn: {
      label: 'Defense resource burn',
      value: replay => resourceBurn(replay, 'defense'),
      format: countFormat,
      delta: countDelta,
    },
    counter_call_count: {
      label: 'Counter calls',
      value: replay => countDefenseCalls(replay, ['redzone_bracket', 'bear_front', 'trap_coverage', 'cover1_man']),
      format: countFormat,
      delta: countDelta,
    },
    counter_graph_events: {
      label: 'Counter graph events',
      value: replay => countEventTags(replay, ['coverage_switch_stress', 'wide_zone_constrained', 'underneath_space_taken']),
      format: countFormat,
      delta: countDelta,
    },
  };
  return metrics[signal] || null;
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
  const structured = filmRoomTweaks({ film_room: room }).map(tweak => `<li>${escapeHtml(tweak.rationale?.rendered || tweak.tweak_id)}</li>`).join('');
  return `<h3>Adaptation Chain</h3><ul>${chain || '<li class="muted">No adaptation chain entries.</li>'}</ul><h3>Notes</h3><ul>${notes || '<li class="muted">-</li>'}</ul><h3>Suggested Tweaks</h3><ul>${tweaks || '<li class="muted">-</li>'}</ul><h3>Structured Tweaks</h3><ul>${structured || '<li class="muted">-</li>'}</ul>`;
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
      <h3>${escapeHtml(launchName(offense.label, 'Offense policy'))} / ${escapeHtml(launchName(defense.label, 'Defense policy'))}</h3>
    </div>
    <p class="compact">${differences.length ? differences.map(item => `${label(item.key)} ${item.delta}`).join(' · ') : 'No local tuning over profile defaults.'}</p>
    <button id="tuneAgent" class="ghost-button" type="button">Ask Assistant</button>
  </div>`;
  $('tuneAgent').onclick = () => dispatchAssistantRequest({ type: 'film_room_tweak', run_id: runtime.replayId || 'seed-42', play_index: CBState.get().selectedIndex + 1 });
}

function compactProfileDiffs(garageState) {
  return ['offense_profile', 'defense_profile'].flatMap(profileKey => {
    const profile = garageState[profileKey] || {};
    const defaults = profileDefaults(profileKey, profile.profile_key);
    const profileParams = profile.parameters || profile;
    const defaultParams = defaults.parameters || defaults;
    return Object.entries(profileParams)
      .filter(([key, raw]) => defaultParams[key] !== undefined && raw !== defaultParams[key])
      .map(([key, raw]) => ({ key, delta: typeof raw === 'number' ? `${raw > defaultParams[key] ? '+' : ''}${(raw - defaultParams[key]).toFixed(2)}` : `${label(defaultParams[key])} → ${label(raw)}` }));
  });
}

function profileDefaults(profileKey, key) {
  const bucket = profileKey === 'defense_profile' ? 'defense_archetypes' : 'offense_archetypes';
  return runtime.profiles[bucket]?.[key] || {};
}

function seedFromReplayId(id) {
  const match = String(id || '').match(/--(\d+)$/) || String(id || '').match(/^seed-(\d+)$/);
  return match ? Number(match[1]) : null;
}

function findProfileKey(side, profile) {
  const bucket = side === 'defense' ? 'defense_archetypes' : 'offense_archetypes';
  if (profile?.profile_key && runtime.profiles[bucket]?.[profile.profile_key]) return profile.profile_key;
  return Object.entries(runtime.profiles[bucket] || {}).find(([, candidate]) => candidate.label === profile?.label)?.[0]
    || Object.keys(runtime.profiles[bucket] || {})[0]
    || '';
}

function garageStateFromReplay(replay, from) {
  const config = structuredClone(replay.agent_garage_config || {});
  const offenseKey = findProfileKey('offense', config.offense_profile);
  const defenseKey = findProfileKey('defense', config.defense_profile);
  const seed = config.runner_seed || seedFromReplayId(from) || garageRunnerSeeds()[0] || 42;
  return {
    source: config.source || 'agent_garage_replay_source',
    offense_profile: { ...(config.offense_profile || runtime.profiles.offense_archetypes?.[offenseKey] || {}), profile_key: offenseKey },
    defense_profile: { ...(config.defense_profile || runtime.profiles.defense_archetypes?.[defenseKey] || {}), profile_key: defenseKey },
    runner_seed: Number(seed),
    draft_controls: { ...(config.draft_controls || {}), runner_seed: String(seed) },
  };
}

function findReplayTweak(replay, tweakId) {
  return filmRoomTweaks(replay).find(tweak => tweak.tweak_id === tweakId) || null;
}

function magnitudeDelta(magnitude) {
  if (typeof magnitude === 'number') return magnitude;
  return { small: 0.1, medium: 0.2, large: 0.3 }[magnitude] || 0.1;
}

function transformedTweakValue(parameter, current, tweak) {
  if (tweak.direction === 'set' && tweak.target_value !== undefined) return tweak.target_value;
  if (numericControls.has(parameter)) {
    const delta = magnitudeDelta(tweak.magnitude);
    const sign = tweak.direction === 'decrease' ? -1 : 1;
    return Math.max(0, Math.min(1, Number((Number(current || 0) + sign * delta).toFixed(2))));
  }
  if (parameter === 'risk_tolerance') {
    const index = Math.max(0, riskOrder.indexOf(String(current)));
    const step = tweak.magnitude === 'large' ? 3 : tweak.magnitude === 'medium' ? 2 : 1;
    const sign = tweak.direction === 'decrease' ? -1 : 1;
    return riskOrder[Math.max(0, Math.min(riskOrder.length - 1, index + sign * step))];
  }
  return tweak.target_value !== undefined ? tweak.target_value : current;
}

function applyTweakToGarageState(garageState, tweak, from) {
  const parameter = tweak.parameter;
  const before = garageControlValueFromState(garageState, parameter);
  const after = transformedTweakValue(parameter, before, tweak);
  garageState.draft_controls = { ...(garageState.draft_controls || {}), [parameter]: after };
  garageState.applied_tweak = {
    ...structuredClone(tweak),
    parent_run_id: from,
    applied_value_before: before,
    applied_value_after: after,
  };
  garageState.parent_run_id = from;
  return garageState.applied_tweak;
}

function garageControlValueFromState(garageState, key) {
  const draft = garageState.draft_controls || {};
  if (draft[key] !== undefined) return draft[key];
  if (key === 'offensive_archetype') return garageState.offense_profile?.profile_key || '';
  if (key === 'defensive_archetype') return garageState.defense_profile?.profile_key || '';
  if (key === 'runner_seed') return String(garageState.runner_seed || garageRunnerSeeds()[0] || 42);
  const offenseParams = garageState.offense_profile?.parameters || garageState.offense_profile || {};
  const defenseParams = garageState.defense_profile?.parameters || garageState.defense_profile || {};
  return offenseParams[key] ?? defenseParams[key] ?? (numericControls.has(key) ? 0.5 : 'balanced');
}

async function prepareGarageFromQuery(params = {}) {
  const from = params.from;
  if (!from) return;
  const key = `${from}:${params.apply || ''}`;
  if (CBState.get().garagePreparedQuery === key) return;
  const replay = await fetchReplayById(from).catch(() => null);
  if (!replay?.agent_garage_config) {
    CBState.set({ garagePreparedQuery: key });
    return;
  }
  const next = garageStateFromReplay(replay, from);
  let applied = null;
  if (params.apply) {
    const tweak = findReplayTweak(replay, params.apply);
    if (tweak) applied = applyTweakToGarageState(next, tweak, from);
  }
  CBState.set({
    garageState: next,
    garageTier: 'declarative',
    garageRules: [],
    garageDraftName: applied ? toHandle(`tweak-${applied.parameter}`) : toHandle(`from-${from}`),
    garagePreparedQuery: key,
    garageHighlightControl: applied?.parameter || null,
  });
  persistGarageActiveDraft();
}

function ensureGarageDefaults() {
  const state = CBState.get();
  const existing = state.garageState || {};
  if (existing.offense_profile && existing.defense_profile) {
    CBState.set({ garageDrafts: loadGarageDrafts() });
    return;
  }
  const activeDraft = loadGarageActiveDraft();
  if (activeDraft?.garageState?.offense_profile && activeDraft?.garageState?.defense_profile) {
    CBState.set({
      garageState: activeDraft.garageState,
      garageTier: activeDraft.garageTier || 'declarative',
      garageRules: activeDraft.garageRules || [],
      garageDraftName: toHandle(activeDraft.name || activeDraft.garageDraftName) || 'coachdraft',
      garageDrafts: loadGarageDrafts(),
    });
    return;
  }
  const offenseKey = Object.keys(runtime.profiles.offense_archetypes || {})[0];
  const defenseKey = Object.keys(runtime.profiles.defense_archetypes || {})[0];
  CBState.set({
    garageState: {
      source: 'agent_garage_profiles_v1',
      offense_profile: { ...(runtime.profiles.offense_archetypes?.[offenseKey] || {}), profile_key: offenseKey },
      defense_profile: { ...(runtime.profiles.defense_archetypes?.[defenseKey] || {}), profile_key: defenseKey },
      draft_controls: {},
    },
    garageDraftName: 'coachdraft',
    garageDrafts: loadGarageDrafts(),
  });
  persistGarageActiveDraft();
}

function renderGaragePage(params = {}) {
  const from = params.from || runtime.replayId || 'seed-42';
  $('garageRouteCopy').textContent = `Tune a fictional coordinator agent, then return to ${from}.`;
  renderTierSelector();
  renderGarageControls();
  renderRuleBuilder();
  renderGarageActions();
  renderGarageDrafts();
  highlightGarageControl(CBState.get().garageHighlightControl);
  mountRows(document.querySelector('[data-route="garage"]'));
}

function highlightGarageControl(key) {
  if (!key) return;
  const row = document.querySelector(`[data-garage-row="${key}"]`);
  if (!row) return;
  row.classList.add('tweak-highlight');
  row.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'center' });
  window.setTimeout(() => {
    row.classList.remove('tweak-highlight');
    if (CBState.get().garageHighlightControl === key) CBState.set({ garageHighlightControl: null });
  }, 2000);
}

function renderTierSelector() {
  document.querySelectorAll('[name="garage_tier"]').forEach(input => {
    input.checked = input.value === CBState.get().garageTier;
    input.onchange = () => {
      CBState.set({ garageTier: input.value });
      persistGarageActiveDraft();
      renderGaragePage(CBRouter.current().params);
    };
  });
  const explainer = $('garageTierExplainer');
  if (explainer) explainer.innerHTML = tierExplainerHtml(CBState.get().garageTier);
}

function renderGarageControls() {
  const tier = CBState.get().garageTier;
  const sections = {
    identity: $('garageIdentityControls'),
    strategy: $('garageStrategyControls'),
    resource: $('garageResourceControls'),
  };
  Object.entries(sections).forEach(([section, target]) => {
    if (!target) return;
    if (section === 'resource') {
      target.innerHTML = renderGarageResourceValidation();
      return;
    }
    const keys = tier === 'remote_endpoint' && !CBState.get().debug && section !== 'identity' ? [] : garageControlKeys(section);
    target.innerHTML = keys.length
      ? keys.map(key => garageControlRow(key)).join('')
      : '<p class="muted compact">Endpoint-owned strategy is hidden outside debug mode.</p>';
  });
  document.querySelectorAll('[data-garage-control]').forEach(input => {
    input.oninput = updateGarageControl;
    input.onchange = updateGarageControl;
  });
}

function tierExplainerHtml(tier) {
  const rows = [
    ['Local presets', 'Declarative policies and legal knobs run through the local replay matrix.'],
    ['Prompt policies', 'Prompt-policy configs are validated before they run.'],
    ['Endpoint policies', 'Endpoint testing stays debug-only.'],
  ];
  const suffix = tier === 'declarative'
    ? 'Current mode: local presets can launch a pre-baked test drive.'
    : 'Current mode: only validated local presets run from this debug panel.';
  return `<p class="muted compact">${rows.map(([name, copy]) => `<strong>${name}</strong>: ${copy}`).join('<br>')}<br>${suffix}</p>`;
}

function garageControlKeys(section) {
  if (section === 'identity') return garageControlSections.identity;
  if (section !== 'strategy') return [];
  const offense = selectedProfile('offense')?.parameters || {};
  const defense = selectedProfile('defense')?.parameters || {};
  const ordered = [...offenseParameterOrder, ...defenseParameterOrder];
  return [...new Set(ordered.filter(key => offense[key] !== undefined || defense[key] !== undefined))];
}

function garageControlRow(key) {
  const current = garageControlValue(key);
  const error = validateGarageControl(key, current);
  const message = error || garageValidationMessage(key);
  const field = numericControls.has(key)
    ? `<input data-garage-control="${key}" type="range" min="0" max="1" step="0.01" value="${current}">`
    : `<select data-garage-control="${key}">${garageOptions(key, current).map(item => `<option value="${escapeHtml(item.value)}" ${item.value === current ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('')}</select>`;
  return `<label class="control-row ${error ? 'has-error' : ''}" data-garage-row="${escapeHtml(key)}">
    <span class="label">${label(key)}</span>
    ${field}
    ${numericControls.has(key) ? `<span class="range-readout">${Math.round(Number(current || 0) * 100)}%</span>` : ''}
    ${garageTooltipHtml(key)}
    <small class="validation-message">${message}</small>
  </label>`;
}

function garageOptions(key, current) {
  if (key === 'offensive_archetype') return archetypeOptions('offense_archetypes', current);
  if (key === 'defensive_archetype') return archetypeOptions('defense_archetypes', current);
  if (key === 'runner_seed') return garageRunnerSeeds().map(value => ({ value: String(value), label: `Seed ${value}` }));
  if (key === 'risk_tolerance') return riskOrder.map(value => ({ value, label: label(value) }));
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
    runner_seed: 'Chooses one fixed pre-baked seed from the local runner matrix.',
    risk_tolerance: 'Controls conservative versus aggressive call selection.',
    adaptation_speed: 'Range 0-1; higher reacts faster to observed patterns.',
    screen_trigger_confidence: 'Range 0-1; minimum confidence before screen counters.',
    explosive_shot_tolerance: 'Range 0-1; higher permits more volatile calls.',
    run_pass_tendency: 'Visible tendency that shifts run, pass, and constraint call mix.',
    disguise_sensitivity: 'Range 0-1; higher reacts more to disguise signals.',
    pressure_frequency: 'Range 0-1; higher calls more pressure looks.',
    counter_repeat_tolerance: 'Range 0-1; lower avoids repeated counters.',
  };
  return help[key] || 'Local coordinator control.';
}

function garageTooltipHtml(key) {
  const glossary = runtime.parameterGlossary[key];
  const fallback = garageHelp(key);
  const football = glossary?.football_terms || fallback;
  const ai = glossary?.ai_terms || 'Sets a visible policy input used by the local preset resolver.';
  return `<small class="help-text garage-tooltip"><span><strong>Football terms:</strong> ${escapeHtml(football)}</span><span><strong>AI terms:</strong> ${escapeHtml(ai)}</span></small>`;
}

function garageValidationMessage(key) {
  if (key === 'runner_seed') return garageRunnerEntries().length ? 'Seed is available in the pre-baked matrix.' : 'Build the garage runner matrix before running.';
  if (key.includes('archetype')) return 'Preset is available in the pre-baked matrix.';
  if (CBState.get().garageTier !== 'declarative') return 'Only validated local presets run here.';
  return 'Legal for the selected local matrix.';
}

function garageControlValue(key) {
  const state = CBState.get().garageState || {};
  const draft = state.draft_controls || {};
  if (draft[key] !== undefined) return draft[key];
  if (key === 'offensive_archetype') return state.offense_profile?.profile_key || Object.keys(runtime.profiles.offense_archetypes || {})[0] || '';
  if (key === 'defensive_archetype') return state.defense_profile?.profile_key || Object.keys(runtime.profiles.defense_archetypes || {})[0] || '';
  if (key === 'runner_seed') return String(garageRunnerSeeds()[0] || 42);
  const offenseParams = state.offense_profile?.parameters || state.offense_profile || {};
  const defenseParams = state.defense_profile?.parameters || state.defense_profile || {};
  return offenseParams[key] ?? defenseParams[key] ?? (numericControls.has(key) ? 0.5 : 'balanced');
}

function updateGarageControl(event) {
  const key = event.target.dataset.garageControl;
  const raw = event.target.type === 'range' ? Number(event.target.value) : event.target.value;
  const next = structuredClone(CBState.get().garageState || {});
  next.draft_controls = { ...(next.draft_controls || {}), [key]: raw };
  if (key === 'offensive_archetype') next.offense_profile = { ...(runtime.profiles.offense_archetypes?.[raw] || {}), profile_key: raw };
  if (key === 'defensive_archetype') next.defense_profile = { ...(runtime.profiles.defense_archetypes?.[raw] || {}), profile_key: raw };
  CBState.set({ garageState: next });
  persistGarageActiveDraft();
  renderGaragePage(CBRouter.current().params);
}

function validateGarageControl(key, raw) {
  if (numericControls.has(key) && (!Number.isFinite(Number(raw)) || Number(raw) < 0 || Number(raw) > 1)) return 'Enter a value from 0 to 1.';
  if ((key.includes('archetype') || key === 'runner_seed' || key === 'risk_tolerance' || key === 'run_pass_tendency') && !raw) return 'Required.';
  if (key === 'runner_seed' && !garageRunnerSeeds().map(String).includes(String(raw))) return 'Pick a seed from the pre-baked matrix.';
  return '';
}

function selectedProfile(side) {
  const bucket = side === 'defense' ? 'defense_archetypes' : 'offense_archetypes';
  const control = side === 'defense' ? 'defensive_archetype' : 'offensive_archetype';
  const key = garageControlValue(control);
  return runtime.profiles[bucket]?.[key] ? { ...runtime.profiles[bucket][key], profile_key: key } : null;
}

function garageRunnerSeeds() {
  const fromIndex = runtime.garageRunnerIndex?.seed_pack || [];
  if (fromIndex.length) return fromIndex;
  const fromEntries = [...new Set(garageRunnerEntries().map(item => Number(item.seed)).filter(Number.isFinite))];
  return fromEntries.length ? fromEntries : [42];
}

function currentGarageParams(side) {
  const profile = selectedProfile(side) || {};
  const params = { ...(profile.parameters || {}) };
  const keys = side === 'defense' ? defenseParameterOrder : offenseParameterOrder;
  keys.forEach(key => {
    const draft = CBState.get().garageState?.draft_controls || {};
    if (draft[key] !== undefined) params[key] = draft[key];
  });
  return params;
}

function profileDistance(params, profileParams) {
  return Object.keys(profileParams || {}).reduce((total, key) => {
    const left = params[key];
    const right = profileParams[key];
    if (typeof right === 'number') return total + Math.abs(Number(left) - right);
    if (key === 'risk_tolerance') {
      const leftIndex = Math.max(0, riskOrder.indexOf(String(left)));
      const rightIndex = Math.max(0, riskOrder.indexOf(String(right)));
      return total + Math.abs(leftIndex - rightIndex) / Math.max(1, riskOrder.length - 1);
    }
    return total + (String(left) === String(right) ? 0 : 1);
  }, 0);
}

function nearestPreset(side) {
  const bucket = side === 'defense' ? 'defense_archetypes' : 'offense_archetypes';
  const params = currentGarageParams(side);
  return Object.entries(runtime.profiles[bucket] || {})
    .map(([key, profile]) => ({ key, profile, distance: profileDistance(params, profile.parameters || {}) }))
    .sort((a, b) => a.distance - b.distance || a.key.localeCompare(b.key))[0] || null;
}

function garageResolvedRunner() {
  const offense = nearestPreset('offense');
  const defense = nearestPreset('defense');
  const seed = Number(garageControlValue('runner_seed'));
  const entry = garageRunnerEntries().find(item =>
    item.offense_preset_id === offense?.key
    && item.defense_preset_id === defense?.key
    && Number(item.seed) === seed
  );
  return {
    offense,
    defense,
    seed,
    entry,
    exact: Boolean(offense && defense && offense.distance === 0 && defense.distance === 0),
  };
}

function renderGarageResourceValidation() {
  const resolved = garageResolvedRunner();
  const errors = garageValidationErrors(resolved);
  const warnings = garageValidationWarnings(resolved);
  const entry = resolved.entry;
  const status = errors.length ? 'is-warn' : warnings.length ? 'is-caution' : 'is-ok';
  const rows = [
    ['Nearest offense preset', resolved.offense?.profile?.label || '-'],
    ['Nearest defense preset', resolved.defense?.profile?.label || '-'],
    ['Runner seed', Number.isFinite(resolved.seed) ? resolved.seed : '-'],
    ['Replay result', entry ? `${label(entry.result)} · ${entry.points} pts · ${entry.plays} plays` : '-'],
  ];
  const list = [...errors, ...warnings, ...(errors.length || warnings.length ? [] : ['Legal-action validation and resource budgets are clean for this pre-baked drive.'])];
  return `<div class="garage-validation ${status}">
    <div class="validation-badge ${errors.length ? 'is-warn' : 'is-ok'}">${errors.length ? 'Blocked' : 'Runnable'}</div>
    ${!resolved.exact && entry ? '<p class="mode-banner garage-nearest-banner">Showing nearest pre-baked drive.</p>' : ''}
    <div class="garage-validation-grid">${rows.map(([name, raw]) => `<div class="kv"><span>${escapeHtml(name)}</span><span>${escapeHtml(raw)}</span></div>`).join('')}</div>
    <ul class="validation-list">${list.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
  </div>`;
}

function garageValidationErrors(resolved = garageResolvedRunner()) {
  const tier = CBState.get().garageTier;
  const controlKeys = [...garageControlKeys('identity'), ...garageControlKeys('strategy')];
  const controlErrors = controlKeys.map(key => validateGarageControl(key, garageControlValue(key))).filter(Boolean);
  const errors = [...controlErrors];
  if (tier !== 'declarative') errors.push('Only validated local presets run locally today.');
  if (!garageRunnerEntries().length) errors.push('No pre-baked garage runner matrix found. Run python scripts/build_garage_runner_matrix.py.');
  if (!resolved.entry) errors.push('No pre-baked replay exists for the resolved preset matchup and seed.');
  if (resolved.entry?.invalid_actions) errors.push('The selected pre-baked drive contains a legal-action validation fallback.');
  if (resolved.entry && resolved.entry.resource_ok === false) errors.push('The selected pre-baked drive exceeds a resource budget.');
  return [...new Set(errors)];
}

function garageValidationWarnings(resolved = garageResolvedRunner()) {
  const warnings = [];
  if (!resolved.exact && resolved.entry) warnings.push('Showing nearest pre-baked drive.');
  return warnings;
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
  persistGarageActiveDraft();
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
  persistGarageActiveDraft();
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
  persistGarageActiveDraft();
  renderGaragePage(CBRouter.current().params);
}

function deleteRule(event) {
  const index = Number(event.target.closest('[data-rule-index]').dataset.ruleIndex);
  CBState.set({ garageRules: (CBState.get().garageRules || []).filter((_, i) => i !== index) });
  persistGarageActiveDraft();
  renderGaragePage(CBRouter.current().params);
}

function renderGarageActions() {
  const button = $('testDriveButton');
  const resolved = garageResolvedRunner();
  const errors = garageValidationErrors(resolved);
  const valid = errors.length === 0;
  button.disabled = !valid;
  button.title = valid ? 'Run the nearest pre-baked drive.' : errors[0] || 'Fix validation errors first.';
  button.classList.toggle('ready', valid);
  button.onclick = runGarageTestDrive;
  const link = $('garageReplayLink');
  if (link) {
    link.hidden = !valid || !resolved.entry;
    link.href = resolved.entry ? replayUrlForRunnerEntry(resolved.entry) : '#';
  }
}

function garageIsValid() {
  return garageValidationErrors().length === 0;
}

function replayUrlForRunnerEntry(entry, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, raw]) => {
    if (raw !== undefined && raw !== null && raw !== '') query.set(key, raw);
  });
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return `app.html#/replays/${encodeURIComponent(entry.id)}${suffix}`;
}

function runGarageTestDrive() {
  const resolved = garageResolvedRunner();
  const errors = garageValidationErrors(resolved);
  if (errors.length || !resolved.entry) {
    renderGaragePage(CBRouter.current().params);
    return;
  }
  const garageState = CBState.get().garageState || {};
  const applied = garageState.applied_tweak;
  const runRecordId = `run-${Date.now().toString(36)}`;
  const run = {
    id: resolved.entry.id,
    run_record_id: runRecordId,
    href: replayUrlForRunnerEntry(resolved.entry, { run: runRecordId }),
    offense: resolved.offense.profile.label,
    defense: resolved.defense.profile.label,
    seed: resolved.seed,
    exact: resolved.exact,
    points: resolved.entry.points,
    result: resolved.entry.result,
    saved_at: new Date().toISOString(),
  };
  if (applied?.parent_run_id) {
    run.parent_run_id = applied.parent_run_id;
    run.parent_href = `app.html#/replays/${encodeURIComponent(applied.parent_run_id)}`;
    run.applied_tweak = applied;
  }
  saveGarageRecentRun(run);
  persistGarageActiveDraft();
  window.location.href = run.href;
}

function renderGarageDrafts() {
  const drafts = loadGarageDrafts();
  const runs = loadGarageRecentRuns();
  CBState.set({ garageDrafts: drafts });
  $('garageDraftName').value = toHandle(CBState.get().garageDraftName) || 'coachdraft';
  $('garageDraftName').oninput = event => {
    const next = toHandle(event.target.value) || 'coachdraft';
    event.target.value = next;
    CBState.set({ garageDraftName: next });
    persistGarageActiveDraft();
  };
  $('saveGarageDraft').onclick = saveGarageDraft;
  $('garageDrafts').innerHTML = `<div class="recent-panel"><h3>Recent Drafts</h3>${
    drafts.length
      ? drafts.map(draft => `<div class="draft-row"><span>${escapeHtml(toHandle(draft.name))}</span><button type="button" data-draft-load="${escapeHtml(draft.name)}">Load</button><button type="button" data-draft-delete="${escapeHtml(draft.name)}">Delete</button></div>`).join('')
      : '<p class="muted compact">No saved drafts in this browser.</p>'
  }</div><div class="recent-panel"><h3>Recent Runs</h3>${
    runs.length
      ? runs.map(run => `<div class="run-row"><a href="${escapeHtml(run.href)}"><span>${escapeHtml(run.offense)} vs ${escapeHtml(run.defense)}</span><small>Seed ${escapeHtml(run.seed)} · ${escapeHtml(label(run.result))} · ${escapeHtml(run.points)} pts${run.exact ? '' : ' · nearest'}</small></a>${run.parent_run_id ? `<a class="parent-run-link" href="${escapeHtml(run.parent_href || `app.html#/replays/${encodeURIComponent(run.parent_run_id)}`)}">Parent run</a>` : ''}</div>`).join('')
      : '<p class="muted compact">No test drives launched in this browser.</p>'
  }</div>`;
  $('garageDrafts').querySelectorAll('[data-draft-load]').forEach(button => button.onclick = loadGarageDraft);
  $('garageDrafts').querySelectorAll('[data-draft-delete]').forEach(button => button.onclick = deleteGarageDraft);
}

function saveGarageDraft() {
  const name = toHandle(CBState.get().garageDraftName) || 'coachdraft';
  const payload = { name, garageState: CBState.get().garageState, garageTier: CBState.get().garageTier, garageRules: CBState.get().garageRules || [], saved_at: new Date().toISOString() };
  try { localStorage.setItem(`${garageDraftPrefix}${name}`, JSON.stringify(payload)); } catch {}
  CBState.set({ garageDraftName: name });
  enforceGarageDraftCap();
  persistGarageActiveDraft();
  renderGaragePage(CBRouter.current().params);
}

function loadGarageDrafts() {
  try {
    return Object.keys(localStorage)
      .filter(key => key.startsWith(garageDraftPrefix))
      .map(key => JSON.parse(localStorage.getItem(key)))
      .sort((a, b) => String(b.saved_at || '').localeCompare(String(a.saved_at || '')) || a.name.localeCompare(b.name))
      .slice(0, garageRecentLimit);
  } catch {
    return [];
  }
}

function enforceGarageDraftCap() {
  try {
    const drafts = Object.keys(localStorage)
      .filter(key => key.startsWith(garageDraftPrefix))
      .map(key => ({ key, value: JSON.parse(localStorage.getItem(key)) }))
      .sort((a, b) => String(b.value.saved_at || '').localeCompare(String(a.value.saved_at || '')) || a.value.name.localeCompare(b.value.name));
    drafts.slice(garageRecentLimit).forEach(item => localStorage.removeItem(item.key));
  } catch {}
}

function loadGarageActiveDraft() {
  try {
    return JSON.parse(localStorage.getItem(garageActiveDraftKey));
  } catch {
    return null;
  }
}

function persistGarageActiveDraft() {
  try {
    localStorage.setItem(garageActiveDraftKey, JSON.stringify({
      name: CBState.get().garageDraftName,
      garageState: CBState.get().garageState,
      garageTier: CBState.get().garageTier,
      garageRules: CBState.get().garageRules || [],
      saved_at: new Date().toISOString(),
    }));
  } catch {}
}

function loadGarageDraft(event) {
  const draft = loadGarageDrafts().find(item => item.name === event.target.dataset.draftLoad);
  if (!draft) return;
  CBState.set({ garageState: draft.garageState, garageTier: draft.garageTier, garageRules: draft.garageRules || [], garageDraftName: toHandle(draft.name) || 'coachdraft' });
  persistGarageActiveDraft();
  renderGaragePage(CBRouter.current().params);
}

function deleteGarageDraft(event) {
  const name = event.target.dataset.draftDelete;
  if (!confirm(`Delete ${name}?`)) return;
  try { localStorage.removeItem(`${garageDraftPrefix}${name}`); } catch {}
  renderGaragePage(CBRouter.current().params);
}

function loadGarageRecentRuns() {
  try {
    const runs = JSON.parse(localStorage.getItem(garageRecentRunsKey) || '[]');
    return Array.isArray(runs) ? runs.slice(0, garageRecentLimit) : [];
  } catch {
    return [];
  }
}

function saveGarageRecentRun(run) {
  try {
    const runs = [run, ...loadGarageRecentRuns().filter(item => item.run_record_id !== run.run_record_id)].slice(0, garageRecentLimit);
    localStorage.setItem(garageRecentRunsKey, JSON.stringify(runs));
  } catch {}
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
    <span class="slate-matchup">${escapeHtml(launchName(match.offense, 'Offense'))} vs ${escapeHtml(launchName(match.defense, 'Defense'))}</span>
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
  if (typeof location === 'undefined' || typeof CBRouter === 'undefined') return;
  if (!location.pathname.endsWith('/replay.html')) return;
  if (CBRouter.current().name !== 'replays') return;
  const seed = new URLSearchParams(location.search).get('seed');
  CBRouter.go('replay-detail', { id: seed ? `seed-${seed}` : 'seed-42' });
}

if (typeof window !== 'undefined') window.CBTopbar?.renderTopbar('replays');
syncMotionPreference();
if (typeof motionQuery.addEventListener === 'function') {
  motionQuery.addEventListener('change', syncMotionPreference);
} else if (typeof motionQuery.addListener === 'function') {
  motionQuery.addListener(syncMotionPreference);
}
if (typeof CBRouter !== 'undefined') {
  normalizeReplayPageRoute();
  CBRouter['subscribe'](route => handleRoute(route).catch(error => {
    document.body.innerHTML = `<pre>Failed to load route: ${error}</pre>`;
  }));
  handleRoute(CBRouter.current()).catch(error => {
    document.body.innerHTML = `<pre>Failed to load route: ${error}</pre>`;
  });
}
