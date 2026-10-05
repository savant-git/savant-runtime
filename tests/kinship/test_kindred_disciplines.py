#!/usr/bin/env python3

from pathlib import Path
import sys


ROOT = Path("/root/savant-runtime")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lexicon.kindred.discipline_engine import (
    DisciplineEngine,
    KindredEdge,
)


def test_eighteen_symmetric_disciplines() -> None:
    engine = DisciplineEngine()

    assert len(engine.disciplines) == 18

    for discipline_id, discipline in engine.disciplines.items():
        assert discipline_id.startswith("discipline:")
        assert discipline["canonical"]
        assert discipline["steward"]
        assert discipline["relations"]

        for relation_id in discipline["relations"]:
            relation = engine.relation(relation_id)
            assert relation["discipline"] == discipline_id


def test_direct_edge_and_inverse_projection() -> None:
    engine = DisciplineEngine()

    edge = KindredEdge(
        subject="instance:opus",
        relation="relation:provides",
        object="capability:generation",
        basis="focused-test",
        authority_state="projected",
    )

    projected = engine.project_edges([edge])

    assert len(projected) == 2

    direct = next(
        item
        for item in projected
        if item["relation"] == "relation:provides"
    )

    inverse = next(
        item
        for item in projected
        if item["relation"] == "relation:provided_by"
    )

    assert direct["discipline"] == "discipline:capability"
    assert direct["steward"] == "Opus"
    assert direct["derived"] is False

    assert inverse["subject"] == "capability:generation"
    assert inverse["object"] == "instance:opus"
    assert inverse["derived"] is True
    assert inverse["authority_state"] == "projected"


def test_existing_kindred_registry_is_untouched() -> None:
    registry = (
        ROOT
        / "lexicon"
        / "kindred"
        / "kindred_registry.yaml"
    )

    assert registry.exists()
