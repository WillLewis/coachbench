(() => {
  const debugFromLocation = () => {
    if (typeof location === 'undefined') return false;
    const search = new URLSearchParams(location.search || '');
    const hashQuery = String(location.hash || '').split('?')[1] || '';
    return search.get('debug') === '1' || new URLSearchParams(hashQuery).get('debug') === '1';
  };
  let state = {
    debug: debugFromLocation(),
    replay: null,
    selectedIndex: 0,
    garageState: {},
    pinnedForCompare: [],
    autoplay: true,
    activeInspectorTab: 'outcome',
    garageTier: 'declarative',
    garageRules: [],
    garageDraftName: 'coachdraft',
    garageDrafts: [],
  };
  const subscribers = new Set();

  window.CBState = {
    get() {
      return state;
    },
    set(patch) {
      state = { ...state, ...patch };
      subscribers.forEach(fn => fn(state));
      return state;
    },
    subscribe(fn) {
      subscribers.add(fn);
      return () => subscribers.delete(fn);
    },
  };
})();
