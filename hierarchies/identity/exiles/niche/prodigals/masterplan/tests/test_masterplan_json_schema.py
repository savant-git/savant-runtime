#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path("/root/savant-runtime")

TOOLS_ROOT = (
    ROOT
    / "tools"
    / "niche"
    / "masterplan"
)

SCHEMA_PATH = (
    ROOT
    / "hierarchies"
    / "identity"
    / "exiles"
    / "niche"
    / "prodigals"
    / "masterplan"
    / "schema"
    / "masterplan_graph.schema.json"
)

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(TOOLS_ROOT),
    )


from validate_masterplan_json_schema import (  # noqa: E402
    deterministic_projection,
    semantic_digest,
)


def authority() -> dict:
    return {
        "state": "authoritative",
        "authority_class": (
            "project-owner-directed"
        ),
        "tier": 0,
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


def graph() -> dict:
    return {
        "schema_version": "1.1.0",
        "graph_id": "savant.masterplan",
        "authority": authority(),
        "records": [
            {
                "id": "SAV-P0-001",
                "kind": "task",
                "title": "Test task",
                "description": "",
                "priority": {
                    "band": "P0",
                    "ordinal": 1,
                    "authority_locked": True,
                    "rationale": "test",
                },
                "status": "active",
                "authority": authority(),
                "purpose": "test",
                "scope": {},
                "acceptance": [
                    "test"
                ],
                "evidence_requirements": [],
                "outputs": [],
                "risks": [],
                "security": {},
                "lineage": {},
                "provenance": provenance(),
                "extensions": {},
            }
        ],
        "segues": [],
        "events": [],
        "decisions": [],
        "evidence": [],
        "receipts": [],
        "attestations": [],
    }


def validator() -> Draft202012Validator:
    schema = json.loads(
        SCHEMA_PATH.read_text(
            encoding="utf-8",
        )
    )

    Draft202012Validator.check_schema(
        schema
    )

    return Draft202012Validator(
        schema
    )


def test_valid_graph_passes() -> None:
    errors = list(
        validator().iter_errors(
            graph()
        )
    )

    assert errors == []


def test_missing_required_collection_fails() -> None:
    value = graph()

    value.pop(
        "events"
    )

    errors = list(
        validator().iter_errors(
            value
        )
    )

    assert errors


def test_invalid_task_identity_fails() -> None:
    value = graph()

    value[
        "records"
    ][0][
        "id"
    ] = "invalid task"

    errors = list(
        validator().iter_errors(
            value
        )
    )

    assert errors


def test_invalid_authority_state_fails() -> None:
    value = graph()

    value[
        "records"
    ][0][
        "authority"
    ][
        "state"
    ] = "imaginary"

    errors = list(
        validator().iter_errors(
            value
        )
    )

    assert errors


def test_invalid_priority_band_fails() -> None:
    value = graph()

    value[
        "records"
    ][0][
        "priority"
    ][
        "band"
    ] = "HIGH"

    errors = list(
        validator().iter_errors(
            value
        )
    )

    assert errors


def test_equal_graphs_have_equal_semantic_digests() -> None:
    first = graph()

    second = copy.deepcopy(
        first
    )

    assert semantic_digest(
        first
    ) == semantic_digest(
        second
    )


def test_volatile_timestamp_does_not_change_digest() -> None:
    first = graph()

    second = copy.deepcopy(
        first
    )

    first[
        "generated_at"
    ] = (
        "2026-08-01T00:00:00+00:00"
    )

    second[
        "generated_at"
    ] = (
        "2027-08-01T00:00:00+00:00"
    )

    assert semantic_digest(
        deterministic_projection(
            first
        )
    ) == semantic_digest(
        deterministic_projection(
            second
        )
    )
