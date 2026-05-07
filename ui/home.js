(() => {
  const PLAY_INTERVAL_MS = 3500;
  const REPLAY_HOLD_MS = 1500;
  const TRANSITION_MS = 350;
  const reducedQuery = typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
  const state = {
    manifest: [],
    cache: new Map(),
    replayIndex: 0,
    playIndex: 0,
    cycleState: reducedQuery.matches ? 'paused' : 'playing',
    timer: null,
    timestampSeed: Date.now(),
  };
  const $ = id => document.getElementById(id);
  const label = raw => String(raw || '').replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase());
  const compact = raw => String(raw || '').replaceAll('_', ' ');

  async function fetchJson(path) {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`${path} ${response.status}`);
    return response.json();
  }

  function seededIndex(seed, count) {
    if (!count) return 0;
    const x = Math.sin(seed) * 10000;
    return Math.floor((x - Math.floor(x)) * count);
  }

  async function initHome() {
    window.CBTopbar?.renderTopbar('home');
    const manifest = await fetchJson('showcase_manifest.json');
    state.manifest = manifest.replays || [];
    state.replayIndex = seededIndex(state.timestampSeed, state.manifest.length);
    await renderCurrentReplay();
    renderGallery();
    wireControls();
    scheduleTick();
    reducedQuery.addEventListener?.('change', handleReducedChange);
  }

  async function loadReplay(item) {
    if (state.cache.has(item.seed)) return state.cache.get(item.seed);
    const replay = await fetchJson(item.replay_path);
    state.cache.set(item.seed, replay);
    return replay;
  }

  async function currentReplay() {
    return loadReplay(state.manifest[state.replayIndex]);
  }

  async function renderCurrentReplay() {
    const item = state.manifest[state.replayIndex];
    const replay = await currentReplay();
    const play = replay.plays[state.playIndex] || replay.plays[0];
    const host = $('homeField');
    if (!host.dataset.ready) {
      host.innerHTML = CBField.fieldHtml('homeBall');
      host.dataset.ready = 'true';
    }
    CBField.positionBall($('homeBall'), play.public.next_state.yardline, play.public.terminal_reason, reducedQuery.matches);
    $('featuredMeta').innerHTML = `<span class="${CBChips.seedDotClass(replay.score?.result)}"></span>FEATURED REPLAY · SEED ${item.seed} · ${item.offense_handle} ⇌ ${item.defense_handle}`;
    $('downsStrip').textContent = CBField.downsText(play);
    $('downsStrip').classList.toggle('is-touchdown', play.public.terminal_reason === 'touchdown');
    $('postDrive').innerHTML = postDriveHtml(item, replay);
    renderTimeline(replay);
  }

  function postDriveHtml(item, replay) {
    const score = replay.score || {};
    return `<p class="eyebrow">Post-drive</p>
      <strong>${label(score.result)}</strong>
      <span>${score.points} pts · ${replay.plays.length} plays</span>
      ${sparkline(item.ep_sparkline || [], score.result)}
      <a class="btn" href="/ui/replay.html?seed=${item.seed}">Open replay</a>`;
  }

  function renderTimeline(replay) {
    $('playPause').textContent = state.cycleState === 'playing' ? '❚❚' : '▶';
    $('timeline').innerHTML = replay.plays.map((_, index) => `<button class="home-play-pill ${index === state.playIndex ? 'active' : ''}" type="button" data-home-play="${index}">Play ${index + 1}</button>`).join('');
    $('timeline').querySelectorAll('[data-home-play]').forEach(button => {
      button.onclick = () => {
        state.cycleState = 'paused';
        clearTimer();
        state.playIndex = Number(button.dataset.homePlay);
        renderCurrentReplay();
      };
    });
    const progress = $('homeProgress');
    progress.classList.remove('running');
    void progress.offsetWidth;
    if (state.cycleState === 'playing' && !reducedQuery.matches) progress.classList.add('running');
  }

  function wireControls() {
    $('playPause').onclick = () => {
      state.cycleState = state.cycleState === 'playing' ? 'paused' : 'playing';
      clearTimer();
      renderCurrentReplay();
      scheduleTick();
    };
  }

  function scheduleTick() {
    clearTimer();
    if (state.cycleState !== 'playing' || reducedQuery.matches) return;
    state.timer = setTimeout(tick, PLAY_INTERVAL_MS);
  }

  async function tick() {
    const replay = await currentReplay();
    if (state.playIndex < replay.plays.length - 1) {
      state.playIndex += 1;
      await renderCurrentReplay();
      scheduleTick();
      return;
    }
    state.cycleState = 'transitioning';
    clearTimer();
    setTimeout(async () => {
      $('featuredShell').classList.add('swapping');
      setTimeout(async () => {
        state.replayIndex = (state.replayIndex + 1) % state.manifest.length;
        state.playIndex = 0;
        state.cycleState = 'playing';
        await renderCurrentReplay();
        $('featuredShell').classList.remove('swapping');
        scheduleTick();
      }, reducedQuery.matches ? 0 : TRANSITION_MS);
    }, REPLAY_HOLD_MS);
  }

  function clearTimer() {
    if (state.timer) clearTimeout(state.timer);
    state.timer = null;
  }

  function renderGallery() {
    CBGallery.render('homeGallery', { replays: state.manifest });
  }

  function sparkline(values, result) {
    const klass = CBChips.sparklineClass('home-sparkline', result);
    const nums = values.length ? values.map(Number) : [0];
    const min = Math.min(...nums), max = Math.max(...nums), range = max - min || 1;
    const x = i => nums.length === 1 ? 2 : 2 + (i / (nums.length - 1)) * 60;
    const y = raw => 22 - ((raw - min) / range) * 18;
    const points = nums.map((raw, index) => `${x(index).toFixed(2)},${y(raw).toFixed(2)}`).join(' ');
    return `<svg class="${klass}" viewBox="0 0 64 24" aria-hidden="true"><path d="M${points.replaceAll(' ', ' L')}"></path></svg>`;
  }

  function handleReducedChange() {
    state.cycleState = reducedQuery.matches ? 'paused' : state.cycleState;
    clearTimer();
    renderCurrentReplay();
    scheduleTick();
  }

  initHome().catch(error => {
    document.body.innerHTML = `<pre>Failed to load home: ${compact(error)}</pre>`;
  });
})();
