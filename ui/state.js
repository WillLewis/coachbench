(() => {
  let state = {
    replay: null,
    selectedIndex: 0,
    garageState: {},
    pinnedForCompare: [],
    autoplay: true,
    activeInspectorTab: 'outcome',
    garageTier: 'declarative',
    garageRules: [],
    garageDraftName: 'coachbench-draft',
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
