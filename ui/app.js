const runtime = { graphCards: {}, conceptLabels: {}, profiles: {}, auto: null, autoScrolling: false, skipNextRouteScroll: false, sharedLoaded: false, replayIndex: null, replaySources: {}, replayId: null };
const $ = id => document.getElementById(id);
const controls = ['offensive_archetype', 'defensive_archetype', 'risk_tolerance', 'adaptation_speed', 'pressure_punish_threshold', 'screen_trigger_confidence', 'explosive_shot_tolerance', 'run_pass_tendency', 'disguise_sensitivity', 'counter_repeat_tolerance', 'resource_conservation'];
const fallbackReplaySources = {
  'seed-42': 'demo_replay.json',
  'static-proof': 'static_proof_replay.json',
};
const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
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
  const source = runtime.replaySources[id] || fallbackReplaySources[id];
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
  renderGarage();
  renderDailySlate();
  renderRosterStrengths();
  renderPlayFeed();
  renderDriveSummary();
  renderFilmRoom();
  setupOverlay();
  setupFeedAutoplay();
  selectPlay(CBState.get().selectedIndex, { syncHash: false, scroll: false, source: 'route' });
  mountRows(document);
  if (!reduced()) runtime.auto.start();
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
    renderRouteStub('garageRouteCopy', 'Coming in Pass 6. ' + CBEmptyStates.emptyAgents());
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
  renderAction('offenseCall', play.public.offense_action);
  renderAction('defenseCall', play.public.defense_action);
  renderOutcome(play.public);
  renderResources(play.public.resource_budget_snapshot, prior && prior.public.resource_budget_snapshot);
  renderEvents(play);
  renderGraphCards(play.public.graph_card_ids || []);
  renderBeliefs(play, prior);
  renderValidation(play.public.validation_result);
  mountPanels(['offenseCall', 'defenseCall', 'playOutcome', 'resources', 'events', 'graphCards', 'beliefs']);
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
  setTimeout(() => { runtime.autoScrolling = false; }, reduced() ? 0 : 260);
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

function renderAction(target, action) {
  $(target).innerHTML = kvRows(action, Object.keys(action));
}

function renderOutcome(play) {
  $('playOutcome').innerHTML = `
    <div class="kv"><span>Yards Gained</span><strong>${play.yards_gained}</strong></div>
    <div class="kv"><span>Expected Value Delta</span><span>${play.expected_value_delta}</span></div>
    <div class="kv"><span>Success</span><span>${play.success ? 'Yes' : 'No'}</span></div>
    <div class="kv"><span>Terminal</span><span>${play.terminal ? 'Yes' : 'No'}</span></div>
    <div class="kv"><span>Terminal Reason</span><span>${value(label(play.terminal_reason))}</span></div>
    <div class="kv"><span>Next State</span><span>${play.next_state.down} & ${play.next_state.distance} at ${play.next_state.yardline}</span></div>
  `;
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
  $('resources').innerHTML = `<div class="resource-grid">${resourceTable(snapshot, prior, 'offense')}${resourceTable(snapshot, prior, 'defense')}</div>`;
}

function renderGraphCards(ids) {
  $('graphCards').innerHTML = ids.map(id => graphCardHtml(runtime.graphCards[id], id)).join('') || `<p class="muted">${CBEmptyStates.emptyGraphEvidence()}</p>`;
}

function graphCardHtml(card, id) {
  if (!card) return `<p class="muted">Card not found: ${id}</p>`;
  const tags = (card.tactical_events || []).map(event => event.tag || event).join(', ');
  return `<div class="card-ref"><h3>${card.name}</h3>${kvRows({ id: card.id, counters: card.counters || [], limitations: (card.limitations || []).join(' '), events: tags }, ['id', 'counters', 'limitations', 'events'])}</div>`;
}

function renderBeliefs(play, prior) {
  const beliefs = play.offense_observed?.belief_after || {};
  const priorBeliefs = prior?.offense_observed?.belief_after || {};
  $('beliefs').innerHTML = Object.entries(beliefs).map(([key, raw]) => {
    const percent = pct(raw);
    const changed = Math.abs(percent - pct(priorBeliefs[key])) >= 10;
    return `<div class="bar"><label><span>${label(key)}</span><span>${percent}%</span></label><div class="meter"><div class="fill ${changed ? 'glow' : ''}" style="width:${percent}%"></div></div></div>`;
  }).join('') || '<p class="muted">No belief data on this play.</p>';
}

function renderEvents(play) {
  const events = play.public.events || [];
  $('events').innerHTML = events.length
    ? events.map(event => `<div class="event-block"><span class="chip">${label(event.tag)}</span><p><strong>${event.graph_card_id}</strong><br>${event.description || ''}</p></div>`).join('')
    : '<p class="muted">No public graph event on this play.</p>';
}

function renderValidation(result) {
  $('validation').innerHTML = result ? `<div class="kv"><span>Validation</span><span>${result.ok ? 'Accepted' : 'Rejected'}</span></div>` : '';
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
  const room = replay.film_room || {};
  const list = items => ((items || []).slice(0, 5).map(item => `<li>${item}</li>`).join('') || '<li class="muted">-</li>') + ((items || []).length > 5 ? `<li class="muted">and ${(items || []).length - 5} more</li>` : '');
  const next = room.next_adjustment ? `<p class="next-adjustment">${room.next_adjustment}</p>` : '';
  $('filmRoom').innerHTML = `<div class="kv"><span>Headline</span><strong>${room.headline || 'Film Room'}</strong></div><div class="kv"><span>Turning Point</span><span>Play ${room.turning_point?.play_index || '-'}</span></div>${next}<h3>Notes</h3><ul>${list(room.notes)}</ul><h3>Suggested Tweaks</h3><ul>${list(room.suggested_tweaks)}</ul>`;
}

function renderGarage() {
  const { replay, garageState } = CBState.get();
  $('garage').innerHTML = `<div class="kv"><span>Offense</span><strong>${replay.agents.offense}</strong></div><div class="kv"><span>Defense</span><strong>${replay.agents.defense}</strong></div><div class="garage-edit-grid">${profileEditor('offense_profile')}${profileEditor('defense_profile')}</div><button id="copyGarage" class="ghost-button" type="button">Copy Profile Payload</button><textarea id="garagePayload" readonly>${garagePayload()}</textarea>`;
  $('copyGarage').onclick = () => navigator.clipboard?.writeText($('garagePayload').value);
  document.querySelectorAll('[data-profile]').forEach(input => input.oninput = updateGarage);
}

function profileEditor(profileKey) {
  const garageState = CBState.get().garageState;
  const profile = garageState[profileKey] || {};
  const set = controls.filter(key => profile[key] !== undefined && profile[key] !== null && profile[key] !== '');
  const missing = controls.filter(key => !set.includes(key)).map(label).join(', ');
  return `<div class="profile-editor"><h3>${label(profileKey)}</h3>${set.map(key => controlInput(profileKey, key, profile[key])).join('')}<p class="muted compact">Other PLAN §5.2 controls not set on this profile: ${missing || '-'}</p></div>`;
}

function controlInput(profileKey, key, current) {
  const numeric = typeof current === 'number';
  if (numeric) return `<label><span class="label">${label(key)}: ${current}</span><input data-profile="${profileKey}" data-key="${key}" type="range" min="0" max="1" step="0.01" value="${current}"></label>`;
  const options = optionValues(key, current).map(item => `<option ${item === current ? 'selected' : ''}>${item}</option>`).join('');
  return `<label><span class="label">${label(key)}</span><select data-profile="${profileKey}" data-key="${key}">${options}</select></label>`;
}

function optionValues(key, current) {
  const profiles = runtime.profiles;
  if (key.includes('archetype')) return [...new Set([current, ...(profiles.offense_archetypes ? Object.values(profiles.offense_archetypes).map(p => p.label) : []), ...(profiles.defense_archetypes ? Object.values(profiles.defense_archetypes).map(p => p.label) : [])])];
  if (key === 'risk_tolerance') return [...new Set([current, 'low', 'medium_low', 'medium', 'medium_high', 'high'])];
  if (key === 'resource_conservation') return [...new Set([current, 'low', 'balanced', 'high'])];
  return [current];
}

function updateGarage(event) {
  const { profile, key } = event.target.dataset;
  const next = structuredClone(CBState.get().garageState);
  next[profile][key] = event.target.type === 'range' ? Number(event.target.value) : event.target.value;
  CBState.set({ garageState: next });
  renderGarage();
}

function garagePayload() {
  const { replay, garageState } = CBState.get();
  return JSON.stringify({ note: 'Paste this payload into a local profile note; browser edits do not rerun the engine.', command: `python scripts/run_showcase.py --seed ${replay.metadata.seed_hash ? 42 : 42} --offense adaptive --defense adaptive --out data/demo_replay.json --copy-ui`, agent_garage_config: garageState }, null, 2);
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
  setTimeout(() => { el.textContent = next; el.style.opacity = '1'; }, reduced() ? 0 : 150);
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
    if (running || count < 2) return;
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
  const raw = getComputedStyle(document.documentElement).getPropertyValue('--autoplay-interval').trim();
  if (raw.endsWith('ms')) return Number(raw.replace('ms', '')) || 3500;
  if (raw.endsWith('s')) return Number(raw.replace('s', '')) * 1000 || 3500;
  return 3500;
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

function mountPanels(ids) { ids.forEach(id => mountRows($(id))); }
function mountRows(root) {
  root.querySelectorAll ? root.querySelectorAll('.row-mount, .panel, #offenseCall, #defenseCall, #playOutcome, #resources, #events, #graphCards, #beliefs').forEach(panel => {
    panel.classList.remove('mount');
    [...panel.children].slice(0, 6).forEach((child, i) => child.style.animationDelay = `${Math.min(i, 6) * 40}ms`);
    void panel.offsetWidth;
    panel.classList.add('mount');
  }) : null;
}

CBRouter.subscribe(route => handleRoute(route).catch(error => {
  document.body.innerHTML = `<pre>Failed to load route: ${error}</pre>`;
}));
handleRoute(CBRouter.current()).catch(error => {
  document.body.innerHTML = `<pre>Failed to load route: ${error}</pre>`;
});
