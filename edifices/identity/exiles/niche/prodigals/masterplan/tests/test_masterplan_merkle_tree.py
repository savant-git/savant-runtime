#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


ROOT = Path("/root/savant-runtime")

TOOLS_ROOT = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
)

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(TOOLS_ROOT),
    )


from build_masterplan_merkle_tree import (  # noqa: E402
    authoritative_leaves,
    build_levels,
    build_merkle_tree,
    pair_digest,
    semantic_digest,
    verify_merkle_tree,
)


def authority() -> dict:
    return {
        "state": "accepted",
        "authority_class": (
            "project-owner-directed"
        ),
        "tier": 1,
        "source": "test",
        "accepted_by": "project-owner",
        "accepted_at": (
            "2026-08-01T00:00:00+00:00"
        ),
        "confidence": 1.0,
    }


def provenance() -> dict:
    return {
        "sources": [],
        "transformations": [],
        "generated_by": "test",
        "generated_at": (
            "2026-08-01T00:00:00+00:00"
        ),
        "contract_version": "1.0.0",
    }


def task(
    task_id: str,
) -> dict:
    return {
        "id": task_id,
        "kind": "task",
        "title": task_id,
        "description": "",
        "priority": {
            "band": "P4A",
            "ordinal": 23,
            "authority_locked": False,
            "rationale": "test",
        },
        "status": "active",
        "authority": authority(),
        "purpose": "test",
        "scope": {},
        "acceptance": [
            "Merkle root is deterministic."
        ],
        "evidence_requirements": [],
        "outputs": [],
        "risks": [],
        "security": {},
        "lineage": {},
        "provenance": provenance(),
        "extensions": {},
    }


def graph() -> dict:
    return {
        "schema_version": "1.1.0",
        "graph_id": "savant.masterplan",
        "authority": authority(),
        "records": [
            task(
                "SAV-P4A-023"
            ),
            task(
                "SAV-P4A-024"
            ),
        ],
        "segues": [
            {
                "id": "segue-test",
                "type": "depends_on",
                "source": "SAV-P4A-024",
                "target": "SAV-P4A-023",
                "authority": authority(),
                "provenance": provenance(),
            }
        ],
        "events": [],
        "decisions": [],
        "evidence": [],
        "receipts": [],
        "attestations": [],
    }


def configure_graph_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    value: dict | None = None,
) -> Path:
    graph_path = (
        tmp_path
        / "masterplan.json"
    )

    graph_value = (
        value
        if value is not None
        else graph()
    )

    graph_path.write_text(
        json.dumps(
            graph_value,
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    module = sys.modules[
        "build_masterplan_merkle_tree"
    ]

    monkeypatch.setattr(
        module,
        "GRAPH_PATH",
        graph_path,
    )

    return graph_path


def test_equal_graphs_produce_equal_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_graph_path(
        tmp_path,
        monkeypatch,
    )

    first = build_merkle_tree(
        graph()
    )

    second = build_merkle_tree(
        copy.deepcopy(
            graph()
        )
    )

    assert (
        first["root_digest"]
        == second["root_digest"]
    )

    assert (
        first["tree_id"]
        == second["tree_id"]
    )


def test_record_change_changes_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_graph_path(
        tmp_path,
        monkeypatch,
    )

    first_graph = graph()

    second_graph = copy.deepcopy(
        first_graph
    )

    second_graph[
        "records"
    ][0][
        "title"
    ] = "Changed"

    first = build_merkle_tree(
        first_graph
    )

    second = build_merkle_tree(
        second_graph
    )

    assert (
        first["root_digest"]
        != second["root_digest"]
    )


def test_leaf_order_is_deterministic() -> None:
    first = graph()

    second = copy.deepcopy(
        first
    )

    second[
        "records"
    ] = list(
        reversed(
            second[
                "records"
            ]
        )
    )

    first_leaves = authoritative_leaves(
        first
    )

    second_leaves = authoritative_leaves(
        second
    )

    assert [
        leaf.to_dict()
        for leaf in first_leaves
    ] == [
        leaf.to_dict()
        for leaf in second_leaves
    ]


def test_odd_leaf_is_duplicated() -> None:
    values = (
        "1" * 64,
        "2" * 64,
        "3" * 64,
    )

    roots, levels = build_levels(
        values
    )

    assert len(
        levels[0]
    ) == 2

    assert (
        levels[0][1].left
        == values[2]
    )

    assert (
        levels[0][1].right
        == values[2]
    )

    assert (
        levels[0][1].digest
        == pair_digest(
            values[2],
            values[2],
        )
    )

    assert len(roots) == 1


def test_empty_graph_has_stable_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = {
        "schema_version": "1.1.0",
        "graph_id": "savant.masterplan",
        "authority": authority(),
        "records": [],
        "segues": [],
        "events": [],
        "decisions": [],
        "evidence": [],
        "receipts": [],
        "attestations": [],
    }

    configure_graph_path(
        tmp_path,
        monkeypatch,
        value,
    )

    first = build_merkle_tree(
        value
    )

    second = build_merkle_tree(
        copy.deepcopy(
            value
        )
    )

    assert (
        first["root_digest"]
        == second["root_digest"]
    )

    assert (
        first["statistics"][
            "leaf_count"
        ]
        == 0
    )


def test_verification_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_graph_path(
        tmp_path,
        monkeypatch,
    )

    value = graph()

    tree = build_merkle_tree(
        value
    )

    verification = verify_merkle_tree(
        tree,
        value,
    )

    assert verification[
        "passed"
    ] is True


def test_tampered_tree_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_graph_path(
        tmp_path,
        monkeypatch,
    )

    value = graph()

    tree = build_merkle_tree(
        value
    )

    tree[
        "root_digest"
    ] = "0" * 64

    verification = verify_merkle_tree(
        tree,
        value,
    )

    assert verification[
        "passed"
    ] is False


def test_semantic_digest_is_key_order_stable() -> None:
    first = {
        "b": 2,
        "a": 1,
    }

    second = {
        "a": 1,
        "b": 2,
    }

    assert semantic_digest(
        first
    ) == semantic_digest(
        second
    )
