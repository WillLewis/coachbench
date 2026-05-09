(() => {
  const label = raw => String(raw || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
  const handle = raw => String(raw || '').toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 16);
  const escapeHtml = raw => String(raw ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

  const sparkline = (values, result) => {
    const klass = CBChips.sparklineClass('home-sparkline', result);
    const nums = values.length ? values.map(Number) : [0];
    const min = Math.min(...nums), max = Math.max(...nums), range = max - min || 1;
    const x = i => nums.length === 1 ? 4 : 4 + (i / (nums.length - 1)) * 112;
    const y = raw => 50 - ((raw - min) / range) * 44;
    const points = nums.map((raw, index) => `${x(index).toFixed(2)},${y(raw).toFixed(2)}`).join(' ');
    return `<svg class="${klass}" viewBox="0 0 120 56" aria-hidden="true"><path d="M${points.replaceAll(' ', ' L')}"></path></svg>`;
  };

  const fieldList = raw => Array.isArray(raw) ? raw : (raw ? [raw] : []);

  const strategyPills = item => {
    const summary = item.summary || {};
    const values = [
      summary.top_concept,
      ...fieldList(summary.concepts),
      ...fieldList(item.concepts),
      ...fieldList(summary.tags),
      ...fieldList(item.tags),
      ...fieldList(summary.counters),
      ...fieldList(item.counters),
    ].filter(Boolean);
    return [...new Set(values.map(String))]
      .slice(0, 4)
      .map(name => `<span class="${CBChips.chipClassFor(name)}">${escapeHtml(label(name))}</span>`)
      .join('');
  };

  const card = item => {
    const result = item.summary?.result;
    const dot = CBChips.seedDotClass(result);
    const offense = handle(item.technical_label?.offense || item.offense_handle || item.offense_label);
    const defense = handle(item.technical_label?.defense || item.defense_handle || item.defense_label);
    const pills = strategyPills(item);
    return `<a class="home-replay-card" href="/ui/replay.html?seed=${encodeURIComponent(item.seed)}">
      <span class="eyebrow"><span class="${dot}"></span>SEED ${escapeHtml(item.seed)}</span>
      <span class="home-card-main">
        <span class="home-card-text">
          <span class="home-card-title">${escapeHtml(offense)} ⇌ ${escapeHtml(defense)}</span>
          <span class="home-card-stat">${escapeHtml(item.summary?.points ?? '-')} pts · ${escapeHtml(label(item.summary?.result))}</span>
          <span class="home-card-stat">${escapeHtml(item.summary?.plays ?? '-')} plays · ${escapeHtml(item.summary?.invalid_action_count ?? '-')} invalid</span>
        </span>
        <span class="home-sparkline-cell">${sparkline(item.ep_sparkline || [], result)}</span>
      </span>
      <span aria-hidden="true"></span>
      ${pills ? `<span class="home-chip-row">${pills}</span>` : '<span class="home-chip-row"></span>'}
    </a>`;
  };

  const render = (targetId, manifest) => {
    const host = document.getElementById(targetId);
    if (!host) return;
    host.innerHTML = (manifest?.replays || []).map(card).join('');
  };

  window.CBGallery = { render, card };
})();
