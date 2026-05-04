let replay, graphCards = {}, conceptLabels = {}, profiles = {}, selectedIndex = 0, garageState = {}, auto = null;
const $ = id => document.getElementById(id);
const controls = ['offensive_archetype', 'defensive_archetype', 'risk_tolerance', 'adaptation_speed', 'pressure_punish_threshold', 'screen_trigger_confidence', 'explosive_shot_tolerance', 'run_pass_tendency', 'disguise_sensitivity', 'counter_repeat_tolerance', 'resource_conservation'];
const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const label = key => conceptLabels[key] || String(key || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const value = item => item === null || item === undefined || item === '' ? '-' : item;
const pct = raw => Math.round(Number(raw || 0) * 100);

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} ${response.status}`);
  return response.json();
}

async function loadReplay() {
  replay = await fetchJson('static_proof_replay.json').catch(() => fetchJson('demo_replay.json'));
  const [graph, concepts, loadedProfiles] = await Promise.all([
    fetchJson('../graph/redzone_v0/interactions.json').catch(() => ({ interactions: [] })),
    fetchJson('../graph/redzone_v0/concepts.json').catch(() => ({ offense: [], defense: [] })),
    fetchJson('../agent_garage/profiles.json').catch(() => ({})),
  ]);
  graphCards = Object.fromEntries((graph.interactions || []).map(card => [card.id, card]));
  [...(concepts.offense || []), ...(concepts.defense || [])].forEach(item => conceptLabels[item.id] = item.label || item.name);
  profiles = loadedProfiles;
  garageState = structuredClone(replay.agent_garage_config || {});
  renderHeader();
  renderGarage();
  renderDailySlate();
  renderTimeline();
  renderDriveSummary();
  renderFilmRoom();
  setupOverlay();
  setupAutoplay();
  selectPlay(0);
  mountRows(document);
  if (!reduced()) auto.start();
}

function renderHeader() {
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

function renderTimeline() {
  $('timeline').innerHTML = '<div id="timelineIndicator" class="timeline-indicator"></div>';
  replay.plays.forEach((play, index) => {
    const btn = document.createElement('button');
    btn.className = 'play';
    btn.type = 'button';
    btn.role = 'tab';
    btn.textContent = `Play ${play.public.play_index}`;
    btn.onclick = () => { auto?.stop(); selectPlay(index); };
    btn.onkeydown = event => handleTimelineKey(event, index);
    $('timeline').appendChild(btn);
  });
  $('timeline').onkeydown = event => {
    if (event.key === ' ') {
      event.preventDefault();
      auto?.toggle();
    }
  };
}

function handleTimelineKey(event, index) {
  if (event.key === 'ArrowRight') { event.preventDefault(); auto?.stop(); focusPlay(Math.min(index + 1, replay.plays.length - 1)); }
  if (event.key === 'ArrowLeft') { event.preventDefault(); auto?.stop(); focusPlay(Math.max(index - 1, 0)); }
  if (event.key === 'Enter') { event.preventDefault(); selectPlay(index); }
}

function focusPlay(index) {
  const btn = document.querySelectorAll('button.play')[index];
  btn.focus();
  selectPlay(index);
}

function selectPlay(index) {
  selectedIndex = index;
  const play = replay.plays[index];
  const prior = index > 0 ? replay.plays[index - 1] : null;
  document.querySelectorAll('button.play').forEach((button, i) => {
    button.classList.toggle('active', i === index);
    button.setAttribute('aria-selected', i === index ? 'true' : 'false');
  });
  moveIndicator();
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
}

function moveIndicator() {
  const active = document.querySelector('button.play.active');
  const indicator = $('timelineIndicator');
  if (!active || !indicator) return;
  indicator.style.width = `${active.offsetWidth}px`;
  indicator.style.transform = `translateX(${active.offsetLeft}px)`;
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
  $('graphCards').innerHTML = ids.map(id => graphCardHtml(graphCards[id], id)).join('') || '<p class="muted">No graph card on this play.</p>';
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
  const room = replay.film_room || {};
  const list = items => ((items || []).slice(0, 5).map(item => `<li>${item}</li>`).join('') || '<li class="muted">-</li>') + ((items || []).length > 5 ? `<li class="muted">and ${(items || []).length - 5} more</li>` : '');
  $('filmRoom').innerHTML = `<div class="kv"><span>Headline</span><strong>${room.headline || 'Film Room'}</strong></div><div class="kv"><span>Turning Point</span><span>Play ${room.turning_point?.play_index || '-'}</span></div><h3>Notes</h3><ul>${list(room.notes)}</ul><h3>Suggested Tweaks</h3><ul>${list(room.suggested_tweaks)}</ul>`;
}

function renderGarage() {
  const cfg = garageState || {};
  $('garage').innerHTML = `<div class="kv"><span>Offense</span><strong>${replay.agents.offense}</strong></div><div class="kv"><span>Defense</span><strong>${replay.agents.defense}</strong></div><div class="garage-edit-grid">${profileEditor('offense_profile')}${profileEditor('defense_profile')}</div><button id="copyGarage" class="ghost-button" type="button">Copy Profile Payload</button><textarea id="garagePayload" readonly>${garagePayload()}</textarea>`;
  $('copyGarage').onclick = () => navigator.clipboard?.writeText($('garagePayload').value);
  document.querySelectorAll('[data-profile]').forEach(input => input.oninput = updateGarage);
}

function profileEditor(profileKey) {
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
  if (key.includes('archetype')) return [...new Set([current, ...(profiles.offense_archetypes ? Object.values(profiles.offense_archetypes).map(p => p.label) : []), ...(profiles.defense_archetypes ? Object.values(profiles.defense_archetypes).map(p => p.label) : [])])];
  if (key === 'risk_tolerance') return [...new Set([current, 'low', 'medium_low', 'medium', 'medium_high', 'high'])];
  if (key === 'resource_conservation') return [...new Set([current, 'low', 'balanced', 'high'])];
  return [current];
}

function updateGarage(event) {
  const { profile, key } = event.target.dataset;
  garageState[profile][key] = event.target.type === 'range' ? Number(event.target.value) : event.target.value;
  renderGarage();
}

function garagePayload() {
  return JSON.stringify({ note: 'Paste this payload into a local profile note; browser edits do not rerun the engine.', command: `python scripts/run_showcase.py --seed ${replay.metadata.seed_hash ? 42 : 42} --offense adaptive --defense adaptive --out data/demo_replay.json --copy-ui`, agent_garage_config: garageState }, null, 2);
}

async function renderDailySlate() {
  const target = $('dailySlate');
  try {
    const slate = await fetchJson('../data/daily_slate/sample_slate.json');
    const results = await fetchJson('../data/daily_slate/results.json').catch(() => ({ results: [] }));
    target.innerHTML = `<div class="slate-grid">${(slate.entries || []).map((entry, i) => slateCard(entry, i, results.results || [])).join('')}</div>`;
  } catch {
    target.innerHTML = '<p class="muted">Daily Slate sample not present.</p>';
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
  const cards = Object.values(graphCards).filter(card => JSON.stringify(card).toLowerCase().includes(query));
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
    state();
    timer = setInterval(() => onTick((selectedIndex + 1) % count), intervalMs);
  };
  const stop = () => {
    if (timer) clearInterval(timer);
    timer = null;
    running = false;
    state();
  };
  return { start, stop, toggle: () => running ? stop() : start(), isRunning: () => running, dispose: stop };
}

function setupAutoplay() {
  auto = createAutoplay({
    count: replay.plays.length,
    intervalMs: 3500,
    onTick: i => selectPlay(i),
    onStateChange: updatePlayPauseButton,
  });
  $('playPause').onclick = () => auto.toggle();
}

function updatePlayPauseButton(running) {
  const button = $('playPause');
  const progress = $('autoplayProgress');
  button.textContent = running ? '❚❚' : '▶';
  button.setAttribute('aria-label', running ? 'Pause autoplay' : 'Play autoplay');
  progress.classList.remove('running');
  void progress.offsetWidth;
  if (running && !reduced()) progress.classList.add('running');
}

function restartAutoplayProgress() {
  if (!auto?.isRunning()) return;
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

loadReplay().catch(error => {
  document.body.innerHTML = `<pre>Failed to load replay: ${error}</pre>`;
});
