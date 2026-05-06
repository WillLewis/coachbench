from __future__ import annotations

from coachbench.graph_loader import StrategyGraph
from coachbench.labels import card_label, concept_label, is_legal_concept


def test_concept_label_uses_graph_label_and_falls_back() -> None:
    assert concept_label("outside_zone") == "Outside Zone"
    assert concept_label("unknown_concept") == "Unknown Concept"


def test_card_label_uses_interaction_name_and_humanizes_unknown_id() -> None:
    graph = StrategyGraph()
    card = graph.interactions[0]

    assert card_label(card["id"]) == card["name"]
    assert card_label("redzone.some_missing_card.v2") == "Some Missing Card"


def test_is_legal_concept_uses_p0_action_vocabulary() -> None:
    assert is_legal_concept("quick_game")
    assert is_legal_concept("redzone_bracket")
    assert not is_legal_concept("edge_contain")
