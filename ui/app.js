let replay = null;
let graphCards = {};

const $ = id => document.getElementById(id);
const label = key => key.replaceAll('_', ' ');
const value = item => item === null || item === undefined || item === '' ? '-' : item;
const controls = ['offensive_archetype', 'defensive_archetype', 'risk_tolerance', 'adaptation_speed', 'pressure_punish_threshold', 'screen_trigger_confidence', 'explosive_shot_tolerance', 'run_pass_tendency', 'disguise_sensitivity', 'counter_repeat_tolerance', 'resource_conservation'];

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} ${response.status}`);
  return response.json();
}

async function loadReplay() {
  replay = await fetchJson('static_proof_replay.json').catch(() => fetchJson('demo_replay.json'));
  const graph = await fetchJson('../graph/redzone_v0/interactions.json').catch(() => ({ interactions: [] }));
  graphCards = Object.fromEntries((graph.interactions || []).map(card => [card.id, card]));
  renderHeader();
  renderGarage();
  renderDailySlate();
  renderTimeline();
  renderDriveSummary();
  renderFilmRoom();
  selectPlay(0);
}

function renderHeader() {
  const mode = replay.metadata.mode;
  $('modeBanner').textContent = mode === 'static_proof'
    ? 'Phase 0B static schema/UI proof - not an engine-generated benchmark result.'
    : 'Engine-generated replay';
  $('modeBanner').classList.toggle('static-proof', mode === 'static_proof');
  $('resultLabel').textContent = label(replay.score.result);
  $('pointsLabel').textContent = `${replay.score.points} pts`;
  $('episodeLabel').textContent = replay.metadata.episode_id;
}

function kvRows(obj, keys) {
  return keys.map(key => `<div class="kv"><span>${label(key)}</span><span>${value(obj[key])}</span></div>`).join('');
}

function profileRows(profile) {
  const set = controls.filter(key => profile[key] !== undefined && profile[key] !== null && profile[key] !== '');
  const missing = controls.filter(key => !set.includes(key)).map(label).join(', ');
  return `
    ${kvRows(profile, set)}
    <p class="muted compact">Other PLAN §5.2 controls not set on this profile: ${missing || '-'}</p>
  `;
}

function renderGarage() {
  const cfg = replay.agent_garage_config || {};
  const offense = cfg.offense_profile || {};
  const defense = cfg.defense_profile || {};
  $('garage').innerHTML = `
    <div class="kv"><span>Offense</span><strong>${replay.agents.offense}</strong></div>
    <div class="kv"><span>Defense</span><strong>${replay.agents.defense}</strong></div>
    <h3>Offense profile</h3>${profileRows(offense)}
    <h3>Defense profile</h3>${profileRows(defense)}
  `;
}

async function renderDailySlate() {
  const target = $('dailySlate');
  try {
    const slate = await fetchJson('../data/daily_slate/sample_slate.json');
    const entries = slate.entries || [];
    target.innerHTML = entries.map((entry, index) => {
      const matchup = entry.matchup || {};
      const name = `${value(matchup.offense)} vs ${value(matchup.defense)}`;
      return `<div class="slate-chip"><strong>${entry.seed || `Entry ${index + 1}`}</strong><span>${name}</span><small>preview not available in static proof</small></div>`;
    }).join('') || '<p class="muted">Daily Slate sample not present</p>';
    target.insertAdjacentHTML('afterbegin', '<p class="muted compact">Phase 0B preview only. Static proof does not fabricate slate results.</p>');
  } catch {
    target.innerHTML = '<p class="muted">Daily Slate sample not present</p>';
  }
}

function renderTimeline() {
  $('timeline').innerHTML = '';
  replay.plays.forEach((play, index) => {
    const btn = document.createElement('button');
    btn.className = 'play';
    btn.textContent = `Play ${play.public.play_index}`;
    btn.onclick = () => selectPlay(index);
    $('timeline').appendChild(btn);
  });
}

function selectPlay(index) {
  document.querySelectorAll('button.play').forEach((button, i) => button.classList.toggle('active', i === index));
  const play = replay.plays[index];
  const prior = index > 0 ? replay.plays[index - 1] : null;
  renderBall(play.public.next_state.yardline);
  renderAction('offenseCall', play.public.offense_action);
  renderAction('defenseCall', play.public.defense_action);
  renderOutcome(play.public);
  renderResources(play.public.resource_budget_snapshot, prior && prior.public.resource_budget_snapshot);
  renderGraphCards(play.public.graph_card_ids || []);
  renderBeliefs(play);
  renderEvents(play);
  renderValidation(play.public.validation_result);
}

function renderBall(yardline) {
  const clamped = Math.max(0, Math.min(25, yardline));
  $('ball').style.left = `${8 + ((25 - clamped) / 25) * 74}%`;
}

function renderAction(target, action) {
  $(''+target).innerHTML = kvRows(action, Object.keys(action));
}

function renderOutcome(play) {
  $('playOutcome').innerHTML = `
    <div class="kv"><span>yards gained</span><strong>${play.yards_gained}</strong></div>
    <div class="kv"><span>expected value delta</span><span>${play.expected_value_delta}</span></div>
    <div class="kv"><span>success</span><span>${play.success}</span></div>
    <div class="kv"><span>terminal</span><span>${play.terminal}</span></div>
    <div class="kv"><span>terminal reason</span><span>${value(play.terminal_reason)}</span></div>
    <div class="kv"><span>next state</span><span>${play.next_state.down} & ${play.next_state.distance} at ${play.next_state.yardline}</span></div>
  `;
}

function resourceRows(snapshot, prior, side) {
  const before = snapshot[`${side}_before`] || {};
  const cost = snapshot[`${side}_cost`] || {};
  const remaining = snapshot[`${side}_remaining`] || {};
  const priorRemaining = prior ? prior[`${side}_remaining`] || {} : null;
  return Object.keys(before).map(resource => {
    const delta = priorRemaining ? remaining[resource] - priorRemaining[resource] : null;
    return { resource, before: before[resource], cost: cost[resource] || 0, remaining: remaining[resource], delta };
  });
}

function resourceTable(snapshot, prior, side) {
  const rows = resourceRows(snapshot, prior, side);
  return `
    <div class="resource-card">
      <h3>${side}</h3>
      <table class="resource-table">
        <thead><tr><th>resource</th><th>before</th><th>cost</th><th>remaining</th><th>Δ</th></tr></thead>
        <tbody>${rows.map(row => `<tr><td>${row.resource}</td><td>${row.before}</td><td>${row.cost}</td><td>${row.remaining}</td><td>${row.delta === null ? '-' : row.delta}</td></tr>`).join('')}</tbody>
      </table>
    </div>
  `;
}

function renderResources(snapshot, prior) {
  $('resources').innerHTML = `<div class="resource-grid">${resourceTable(snapshot, prior, 'offense')}${resourceTable(snapshot, prior, 'defense')}</div>`;
}

function renderGraphCards(ids) {
  $('graphCards').innerHTML = ids.map(id => {
    const card = graphCards[id];
    if (!card) return `<p class="muted">Card not found: ${id}</p>`;
    const tags = (card.tactical_events || []).map(event => event.tag || event).join(', ');
    return `
      <div class="card-ref">
        <h3>${card.name}</h3>
        <div class="kv"><span>ID</span><span>${id}</span></div>
        <div class="kv"><span>Counters</span><span>${(card.counters || []).join(', ') || '-'}</span></div>
        <div class="kv"><span>Limitations</span><span>${(card.limitations || []).join(' ') || '-'}</span></div>
        <div class="kv"><span>Events</span><span>${tags || '-'}</span></div>
      </div>
    `;
  }).join('') || '<p class="muted">No graph card on this play.</p>';
}

function renderBeliefs(play) {
  const beliefs = (play.offense_observed || {}).belief_after || {};
  $('beliefs').innerHTML = Object.entries(beliefs).map(([key, raw]) => {
    const pct = Math.round(Number(raw) * 100);
    return `<div class="bar"><label><span>${label(key)}</span><span>${pct}%</span></label><div class="meter"><div class="fill" style="width:${pct}%"></div></div></div>`;
  }).join('');
}

function renderEvents(play) {
  const events = play.public.events || [];
  $('events').innerHTML = events.length
    ? events.map(event => `<div class="chip">${event.tag}</div><p><strong>${event.graph_card_id}</strong><br>${event.description}</p>`).join('')
    : '<p class="muted">No public graph event on this play.</p>';
}

function renderValidation(result) {
  $('validation').innerHTML = result ? `<div class="kv"><span>Validation</span><span>${result.ok ? 'ok' : 'rejected'}</span></div>` : '';
}

function renderDriveSummary() {
  const last = replay.plays[replay.plays.length - 1].public;
  $('driveSummary').innerHTML = `
    <div class="kv"><span>Result</span><strong>${label(replay.score.result)}</strong></div>
    <div class="kv"><span>Points</span><span>${replay.score.points}</span></div>
    <div class="kv"><span>Plays played</span><span>${replay.plays.length}</span></div>
    <div class="kv"><span>Terminal reason</span><span>${value(last.terminal_reason)}</span></div>
    <p class="muted">Drive ended at yardline ${last.next_state.yardline} after play ${last.play_index}.</p>
  `;
}

function renderFilmRoom() {
  const room = replay.film_room || {};
  const list = items => {
    const visible = (items || []).slice(0, 5).map(item => `<li>${item}</li>`).join('');
    const extra = (items || []).length > 5 ? `<li class="muted">and ${(items || []).length - 5} more</li>` : '';
    return visible + extra || '<li class="muted">-</li>';
  };
  $('filmRoom').innerHTML = `
    <div class="kv"><span>Headline</span><strong>${room.headline || 'Film Room'}</strong></div>
    <div class="kv"><span>Turning point</span><span>Play ${(room.turning_point || {}).play_index || '-'}</span></div>
    <h3>Notes</h3><ul>${list(room.notes)}</ul>
    <h3>Suggested tweaks</h3><ul>${list(room.suggested_tweaks)}</ul>
  `;
}

loadReplay().catch(error => {
  document.body.innerHTML = `<pre>Failed to load replay: ${error}</pre>`;
});
