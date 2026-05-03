let replay = null;
let selectedIndex = 0;

async function loadReplay() {
  const response = await fetch('demo_replay.json');
  replay = await response.json();
  renderHeader();
  renderGarage();
  renderTimeline();
  renderFilmRoom();
  selectPlay(0);
}

function renderHeader() {
  document.getElementById('resultLabel').textContent = replay.score.result.replace('_', ' ');
  document.getElementById('pointsLabel').textContent = `${replay.score.points} pts`;
  document.getElementById('episodeLabel').textContent = replay.metadata.episode_id;
}

function renderGarage() {
  const cfg = replay.agent_garage_config || {};
  document.getElementById('garage').innerHTML = `
    <div class="kv"><span>Offense</span><strong>${replay.agents.offense}</strong></div>
    <div class="kv"><span>Defense</span><strong>${replay.agents.defense}</strong></div>
    <div class="kv"><span>Offense archetype</span><span>${cfg.offense_archetype || 'Starter'}</span></div>
    <div class="kv"><span>Defense archetype</span><span>${cfg.defense_archetype || 'Starter'}</span></div>
  `;
}

function renderTimeline() {
  const timeline = document.getElementById('timeline');
  timeline.innerHTML = '';
  replay.plays.forEach((play, index) => {
    const btn = document.createElement('button');
    btn.className = 'play';
    btn.textContent = `Play ${play.play_index}`;
    btn.onclick = () => selectPlay(index);
    timeline.appendChild(btn);
  });
}

function selectPlay(index) {
  selectedIndex = index;
  document.querySelectorAll('button.play').forEach((button, i) => {
    button.classList.toggle('active', i === index);
  });
  const play = replay.plays[index];
  renderBall(play.next_state.yardline);
  renderPlayDetails(play);
  renderBeliefs(play);
  renderEvents(play);
}

function renderBall(yardline) {
  const ball = document.getElementById('ball');
  const clamped = Math.max(0, Math.min(25, yardline));
  const leftPercent = 8 + ((25 - clamped) / 25) * 74;
  ball.style.left = `${leftPercent}%`;
}

function renderPlayDetails(play) {
  document.getElementById('playDetails').innerHTML = `
    <div class="kv"><span>Outcome</span><strong>${play.yards_gained} yards</strong></div>
    <div class="kv"><span>Expected value</span><span>${play.expected_value_delta}</span></div>
    <div class="kv"><span>Offense</span><span>${play.offense_action.concept_family}</span></div>
    <div class="kv"><span>Defense</span><span>${play.defense_action.coverage_family}</span></div>
    <div class="kv"><span>Next state</span><span>${play.next_state.down} & ${play.next_state.distance} at ${play.next_state.yardline}</span></div>
    <div class="kv"><span>Terminal</span><span>${play.terminal_reason || 'no'}</span></div>
  `;
}

function renderBeliefs(play) {
  const beliefs = play.offense_belief_after || {};
  const rows = Object.entries(beliefs).map(([key, value]) => {
    const pct = Math.round(Number(value) * 100);
    return `
      <div class="bar">
        <label><span>${key.replaceAll('_', ' ')}</span><span>${pct}%</span></label>
        <div class="meter"><div class="fill" style="width:${pct}%"></div></div>
      </div>
    `;
  }).join('');
  document.getElementById('beliefs').innerHTML = rows;
}

function renderEvents(play) {
  const events = play.events || [];
  if (!events.length) {
    document.getElementById('events').innerHTML = '<p class="muted">No high-leverage graph event on this play.</p>';
    return;
  }
  document.getElementById('events').innerHTML = events.map(event => `
    <div class="chip">${event.tag}</div>
    <p><strong>${event.graph_card_id}</strong><br>${event.description}</p>
  `).join('');
}

function renderFilmRoom() {
  const room = replay.film_room || {};
  const notes = (room.notes || []).map(note => `<li>${note}</li>`).join('');
  const tweaks = (room.suggested_tweaks || []).map(tweak => `<li>${tweak}</li>`).join('');
  document.getElementById('filmRoom').innerHTML = `
    <div class="kv"><span>Headline</span><strong>${room.headline || 'Film Room'}</strong></div>
    <div class="kv"><span>Turning point</span><span>Play ${(room.turning_point || {}).play_index || '-'}</span></div>
    <h3>Notes</h3>
    <ul>${notes}</ul>
    <h3>Suggested tweaks</h3>
    <ul>${tweaks}</ul>
  `;
}

loadReplay().catch(error => {
  document.body.innerHTML = `<pre>Failed to load replay: ${error}</pre>`;
});
