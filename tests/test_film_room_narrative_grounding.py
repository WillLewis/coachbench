from __future__ import annotations

import json
from pathlib import Path

from coachbench.film_room import narrative_for_drive
from coachbench.graph_loader import StrategyGraph
from coachbench.labels import card_label, concept_label


SHOWCASE_REPLAYS = sorted(Path("ui/showcase_replays").glob("seed_*.json"))


def _observed_card_ids(replay: dict) -> set[str]:
    return {
        str(card_id)
        for play in replay["plays"]
        for card_id in play["public"].get("graph_card_ids", [])
    }


def _observed_concepts(replay: dict) -> set[str]:
    concepts: set[str] = set()
    for play in replay["plays"]:
        public = play["public"]
        offense = public.get("offense_action", {}).get("concept_family")
        defense = public.get("defense_action", {}).get("coverage_family")
        if offense:
            concepts.add(str(offense))
        if defense:
            concepts.add(str(defense))
    return concepts


def test_showcase_narratives_only_use_observed_card_and_concept_labels() -> None:
    graph = StrategyGraph()
    all_card_labels = {card_label(card["id"], graph): card["id"] for card in graph.interactions}
    all_concept_labels = {
        concept_label(concept_id, graph): concept_id
        for concept_id in [*graph.offense_concepts(), *graph.defense_calls()]
    }

    for path in SHOWCASE_REPLAYS:
        replay = json.loads(path.read_text(encoding="utf-8"))
        narrative = narrative_for_drive(replay["film_room"], replay["plays"], graph)
        assert narrative == replay["film_room"]["narrative"]
        if narrative is None:
            continue
        observed_cards = _observed_card_ids(replay)
        observed_concepts = _observed_concepts(replay)
        present_card_ids = {
            card_id
            for label, card_id in all_card_labels.items()
            if label in narrative
        }
        present_concepts = {
            concept_id
            for label, concept_id in all_concept_labels.items()
            if label in narrative
        }
        assert present_card_ids
        assert present_card_ids <= observed_cards
        assert present_concepts
        assert present_concepts <= observed_concepts
