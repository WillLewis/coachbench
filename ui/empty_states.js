(() => {
  window.CBEmptyStates = {
    emptyReplays: () => 'No replays yet — run `make demo`.',
    emptyAgents: () => 'Start with a Tier 0 archetype.',
    emptyGraphEvidence: () => 'No graph evidence fired on this play.',
    emptySlate: () => 'No Daily Slate results yet — static preview.',
    notFoundReplay: id => `Replay \`${id}\` not found.`,
  };
})();
