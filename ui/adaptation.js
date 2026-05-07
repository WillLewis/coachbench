(() => {
  const publicPlay = play => play.public || play;
  const beliefs = play => publicPlay(play).beliefs || play.offense_observed?.belief_after || {};
  const graphCardIds = play => publicPlay(play).graph_card_ids || [];
  const offenseCall = play => publicPlay(play).offense_action?.concept_family || null;
  const defenseCall = play => publicPlay(play).defense_action?.coverage_family || null;
  const cardMap = graphCards => Array.isArray(graphCards)
    ? Object.fromEntries(graphCards.map(card => [card.id, card]))
    : graphCards;

  function classifyAdaptationReasons(plays, graphCards) {
    const cards = cardMap(graphCards || {});
    const seen = new Set();
    const reasons = {};

    plays.forEach((play, index) => {
      const currentCards = graphCardIds(play);
      if (currentCards.some(id => !seen.has(id))) {
        reasons[index] = 'graph-fire';
      }

      if (index > 0 && !reasons[index]) {
        const priorBeliefs = beliefs(plays[index - 1]);
        const currentBeliefs = beliefs(play);
        const keys = new Set([...Object.keys(priorBeliefs), ...Object.keys(currentBeliefs)]);
        for (const key of keys) {
          if (Math.abs(Number(currentBeliefs[key] || 0) - Number(priorBeliefs[key] || 0)) >= 0.10) {
            reasons[index] = 'belief-shift';
            break;
          }
        }
      }

      if (index > 0 && !reasons[index]) {
        const counters = new Set(graphCardIds(plays[index - 1]).flatMap(id => cards[id]?.counters || []));
        const offenseCounter = offenseCall(play) !== offenseCall(plays[index - 1]) && counters.has(offenseCall(play));
        const defenseCounter = defenseCall(play) !== defenseCall(plays[index - 1]) && counters.has(defenseCall(play));
        if (offenseCounter || defenseCounter) reasons[index] = 'counter-call';
      }

      currentCards.forEach(id => seen.add(id));
    });

    return reasons;
  }

  function classifyAdaptation(plays, graphCards) {
    return new Set(Object.keys(classifyAdaptationReasons(plays, graphCards)).map(Number));
  }

  window.CBAdaptation = { classifyAdaptation, classifyAdaptationReasons };
})();
