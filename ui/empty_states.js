(() => {
  window.CBEmptyStates = {
    emptyReplays: () => 'No replays yet — run `make demo`.',
    emptyAgents: () => 'Start with a validated local archetype.',
    emptyGraphEvidence: () => 'No graph cards fired on this play.',
    emptySlate: () => 'No Daily Slate results yet — static preview.',
    notFoundReplay: id => `Replay \`${id}\` not found.`,
  };
})();
