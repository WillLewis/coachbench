(() => {
  const ROUTES = [
    { name: 'replays', path: '/replays', pattern: /^\/replays\/?$/, build: () => '/replays' },
    { name: 'replay-detail', path: '/replays/:id', pattern: /^\/replays\/([^/]+)\/?$/, build: params => `/replays/${encodeURIComponent(params.id || 'seed-42')}` },
    { name: 'garage', path: '/garage', pattern: /^\/garage\/?$/, build: () => '/garage' },
    { name: 'reports', path: '/reports', pattern: /^\/reports\/?$/, build: () => '/reports' },
    { name: 'arena', path: '/arena', pattern: /^\/arena\/?$/, build: () => '/arena' },
  ];
  const DEFAULT_HASH = '#/replays';
  const subscribers = new Set();

  function pathFromHash() {
    return location.hash.replace(/^#/, '') || '/replays';
  }

  function match(path) {
    for (const route of ROUTES) {
      const found = path.match(route.pattern);
      if (found) {
        return {
          name: route.name,
          params: route.name === 'replay-detail' ? { id: decodeURIComponent(found[1]) } : {},
        };
      }
    }
    return { name: 'replays', params: {} };
  }

  function isKnown(path) {
    return ROUTES.some(route => route.pattern.test(path));
  }

  function notify() {
    const route = window.CBRouter.current();
    subscribers.forEach(fn => fn(route));
  }

  window.CBRouter = {
    current() {
      return match(pathFromHash());
    },
    subscribe(fn) {
      subscribers.add(fn);
      return () => subscribers.delete(fn);
    },
    go(name, params = {}) {
      const route = ROUTES.find(item => item.name === name);
      const next = `#${(route || ROUTES[0]).build(params)}`;
      if (location.hash !== next) location.hash = next;
    },
  };

  window.addEventListener('hashchange', notify);
  if (!location.hash || !isKnown(pathFromHash())) location.hash = DEFAULT_HASH;
})();
