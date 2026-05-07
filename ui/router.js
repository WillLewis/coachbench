(() => {
  const ROUTES = [
    { name: 'replays', path: '/replays', pattern: /^\/replays\/?$/, build: () => '/replays' },
    { name: 'replay-detail', path: '/replays/:id', pattern: /^\/replays\/([^/]+)\/?$/, build: params => `/replays/${encodeURIComponent(params.id || 'seed-42')}${buildQuery(params, ['id'])}` },
    { name: 'garage', path: '/garage', pattern: /^\/garage\/?$/, build: () => '/garage' },
    { name: 'reports', path: '/reports', pattern: /^\/reports\/?$/, build: params => `/reports${params.compare ? `?compare=${String(params.compare).split(',').map(encodeURIComponent).join(',')}` : ''}` },
    { name: 'arena', path: '/arena', pattern: /^\/arena\/?$/, build: () => '/arena' },
  ];
  const DEFAULT_HASH = '#/replays';
  const subscribers = new Set();

  function buildQuery(params, omit = []) {
    const query = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, raw]) => {
      if (!omit.includes(key) && key !== 'query' && raw !== undefined && raw !== null && raw !== '') query.set(key, raw);
    });
    const text = query.toString();
    return text ? `?${text}` : '';
  }

  function splitHash() {
    const raw = location.hash.replace(/^#/, '') || '/replays';
    const [path, query = ''] = raw.split('?');
    return { path, query };
  }

  function queryParams(query) {
    return Object.fromEntries(new URLSearchParams(query));
  }

  function match(path, query) {
    for (const route of ROUTES) {
      const found = path.match(route.pattern);
      if (found) {
        const queryObject = queryParams(query);
        return {
          name: route.name,
          params: route.name === 'replay-detail' ? { ...queryObject, query: queryObject, id: decodeURIComponent(found[1]) } : { ...queryObject, query: queryObject },
        };
      }
    }
    return { name: 'replays', params: { query: {} } };
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
      const { path, query } = splitHash();
      return match(path, query);
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
  if (!location.hash || !isKnown(splitHash().path)) location.hash = DEFAULT_HASH;
})();
