(() => {
  const pages = [
    ['home', 'Home', '/ui/index.html'],
    ['replays', 'Film Room', '/ui/app.html#/replays'],
    ['garage', 'Workbench', '/ui/app.html#/garage'],
    ['reports', 'Reports', '/ui/app.html#/reports'],
    ['arena', 'Arena', '/ui/app.html#/arena'],
  ];

  function renderTopbar(activePage = 'home') {
    const host = document.getElementById('topbar');
    if (!host) return;
    host.innerHTML = `<header class="topbar" data-topbar>
      <a class="wordmark" href="/ui/index.html">CoachBench</a>
      <nav class="topbar-nav" aria-label="Primary">${pages.map(([key, label, href]) => `<a class="topbar-link ${key === activePage ? 'active' : ''}" href="${href}" ${key === activePage ? 'aria-current="page"' : ''}>${label}</a>`).join('')}</nav>
      <button class="topbar-burger icon-btn" type="button" aria-expanded="false" aria-controls="topbarDropdown">☰</button>
      <nav id="topbarDropdown" class="topbar-dropdown" aria-label="Primary mobile" hidden>${pages.map(([key, label, href]) => `<a class="topbar-link ${key === activePage ? 'active' : ''}" href="${href}" ${key === activePage ? 'aria-current="page"' : ''}>${label}</a>`).join('')}</nav>
    </header>`;
    const burger = host.querySelector('.topbar-burger');
    const dropdown = host.querySelector('.topbar-dropdown');
    const close = () => {
      dropdown.hidden = true;
      burger.setAttribute('aria-expanded', 'false');
    };
    burger.onclick = event => {
      event.stopPropagation();
      dropdown.hidden = !dropdown.hidden;
      burger.setAttribute('aria-expanded', dropdown.hidden ? 'false' : 'true');
    };
    dropdown.querySelectorAll('a').forEach(link => link.addEventListener('click', close));
    document.addEventListener('click', event => {
      if (!host.contains(event.target)) close();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') close();
    });
  }

  window.CBTopbar = { renderTopbar };
  window.renderTopbar = renderTopbar;
})();
