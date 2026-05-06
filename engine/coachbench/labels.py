from __future__ import annotations

from functools import lru_cache

from .graph_loader import StrategyGraph


def _humanize(value: str) -> str:
    return " ".join(part for part in value.replace(".", " ").replace("_", " ").split()).title()


@lru_cache(maxsize=None)
def _default_concept_labels() -> dict[str, str]:
    graph = StrategyGraph()
    return {
        item["id"]: item.get("name") or item.get("label") or _humanize(item["id"])
        for item in [*graph.concepts.get("offense", []), *graph.concepts.get("defense", [])]
    }


@lru_cache(maxsize=None)
def _default_card_labels() -> dict[str, str]:
    graph = StrategyGraph()
    return {card["id"]: card.get("name") or _humanize(card["id"]) for card in graph.interactions}


@lru_cache(maxsize=None)
def _default_legal_ids() -> frozenset[str]:
    graph = StrategyGraph()
    return frozenset([*graph.offense_concepts(), *graph.defense_calls()])


def _concept_labels_for_graph(graph: StrategyGraph) -> dict[str, str]:
    return {
        item["id"]: item.get("name") or item.get("label") or _humanize(item["id"])
        for item in [*graph.concepts.get("offense", []), *graph.concepts.get("defense", [])]
    }


def _card_labels_for_graph(graph: StrategyGraph) -> dict[str, str]:
    return {card["id"]: card.get("name") or _humanize(card["id"]) for card in graph.interactions}


def _card_fallback(card_id: str) -> str:
    parts = card_id.split(".")
    if parts and parts[0] == "redzone":
        parts = parts[1:]
    if parts and parts[-1].startswith("v") and parts[-1][1:].isdigit():
        parts = parts[:-1]
    return _humanize(" ".join(parts) or card_id)


def concept_label(concept_id: str, graph: StrategyGraph | None = None) -> str:
    labels = _concept_labels_for_graph(graph) if graph else _default_concept_labels()
    return labels.get(concept_id, _humanize(concept_id))


def card_label(card_id: str, graph: StrategyGraph | None = None) -> str:
    labels = _card_labels_for_graph(graph) if graph else _default_card_labels()
    return labels.get(card_id, _card_fallback(card_id))


def is_legal_concept(concept_id: str, graph: StrategyGraph | None = None) -> bool:
    if graph:
        return concept_id in set([*graph.offense_concepts(), *graph.defense_calls()])
    return concept_id in _default_legal_ids()
