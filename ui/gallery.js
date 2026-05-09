(() => {
  const label = raw => String(raw || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
  const handle = raw => String(raw || '').toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 16);
  const escapeHtml = raw => String(raw ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

  const sparkline = (values, result) => {
    const klass = CBChips.sparklineClass('home-sparkline', result);
    const nums = values.length ? values.map(Number) : [0];
    const min = Math.min(...nums), max = Math.max(...nums), range = max - min || 1;
    const x = i => nums.length === 1 ? 2 : 2 + (i / (nums.length - 1)) * 60;
    const y = raw => 22 - ((raw - min) / range) * 18;
    const points = nums.map((raw, index) => `${x(index).toFixed(2)},${y(raw).toFixed(2)}`).join(' ');
    return `<svg class="${klass}" viewBox="0 0 64 24" aria-hidden="true"><path d="M${points.replaceAll(' ', ' L')}"></path></svg>`;
  };

  const card = item => {
    const result = item.summary?.result;
    const dot = CBChips.seedDotClass(result);
    const conceptClass = CBChips.chipClassFor(item.summary?.top_concept);
    const conceptText = label(item.summary?.top_concept);
    return `<a class="home-replay-card" href="/ui/replay.html?seed=${encodeURIComponent(item.seed)}">
      <span class="eyebrow"><span class="${dot}"></span>SEED ${escapeHtml(item.seed)}</span>
      <strong>${escapeHtml(item.offense_label || handle(item.offense_handle))} ⇌ ${escapeHtml(item.defense_label || handle(item.defense_handle))}</strong>
      <span class="muted">${escapeHtml(item.summary?.points ?? '-')} pts · ${escapeHtml(label(item.summary?.result))}</span>
      <span class="muted">${escapeHtml(item.summary?.plays ?? '-')} plays · ${escapeHtml(item.summary?.invalid_action_count ?? '-')} invalid</span>
      ${sparkline(item.ep_sparkline || [], result)}
      <span class="home-chip-row">
        <span class="${conceptClass}">${escapeHtml(conceptText)}</span>
      </span>
    </a>`;
  };

  const render = (targetId, manifest) => {
    const host = document.getElementById(targetId);
    if (!host) return;
    host.innerHTML = (manifest?.replays || []).map(card).join('');
  };

  window.CBGallery = { render, card };
})();
