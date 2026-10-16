#!/usr/bin/env python3
"""Deterministic, non-authoritative character scenario analysis."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from guise_composition import TRAITS


class GuiseScenarioError(ValueError):
    """Invalid scenario input or character evidence."""


SCHEMA = "savant://carbon/oriel/guise/scenario/1"

MOTES = frozenset(
    mote
    for motes in TRAITS.values()
    for mote in motes
)


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical(value).encode("utf-8")
    ).hexdigest()


def required(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise GuiseScenarioError(
            f"{field} must be text"
        )

    if not value or value != value.strip():
        raise GuiseScenarioError(
            f"{field} must be nonempty and normalized"
        )

    return value


def normalize_scenario(
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize a hypothetical situation without granting authority."""

    if not isinstance(scenario, Mapping):
        raise GuiseScenarioError(
            "scenario must be a mapping"
        )

    character = required(
        scenario.get("character"),
        "character",
    )
    situation = required(
        scenario.get("situation"),
        "situation",
    )

    pressures = scenario.get("pressures", [])

    if not isinstance(pressures, list):
        raise GuiseScenarioError(
            "pressures must be a list"
        )

    normalized_pressures = []

    for pressure in pressures:
        if not isinstance(pressure, Mapping):
            raise GuiseScenarioError(
                "pressure must be a mapping"
            )

        mote = required(
            pressure.get("mote"),
            "pressure mote",
        )

        if mote not in MOTES:
            raise GuiseScenarioError(
                f"unknown mote: {mote}"
            )

        intensity = pressure.get("intensity")

        if (
            isinstance(intensity, bool)
            or not isinstance(intensity, int)
            or not 0 <= intensity <= 100
        ):
            raise GuiseScenarioError(
                "intensity must be an integer from 0 to 100"
            )

        normalized_pressures.append(
            {
                "mote": mote,
                "intensity": intensity,
            }
        )

    normalized_pressures.sort(
        key=lambda item: (
            item["mote"],
            item["intensity"],
        )
    )

    result = {
        "schema": SCHEMA,
        "character": character,
        "situation": situation,
        "pressures": normalized_pressures,
    }

    result["identity"] = (
        "guise:scenario:"
        + digest(result)[:32]
    )

    return result


def evaluate(
    scenario: Mapping[str, Any],
    evidence_view: Mapping[str, Any],
) -> dict[str, Any]:
    """Relate hypothetical pressures to existing character evidence.

    This function identifies supporting material. It does not predict
    actions, calculate psychological probabilities, or establish canon.
    """

    normalized = normalize_scenario(scenario)

    if not isinstance(evidence_view, Mapping):
        raise GuiseScenarioError(
            "evidence view must be a mapping"
        )

    if evidence_view.get("character") != normalized["character"]:
        raise GuiseScenarioError(
            "character identity mismatch"
        )

    if evidence_view.get("authoritative") is not False:
        raise GuiseScenarioError(
            "expected a non-authoritative evidence projection"
        )

    evidence = evidence_view.get("evidence")

    if not isinstance(evidence, list):
        raise GuiseScenarioError(
            "evidence must be a list"
        )

    indexed: dict[str, list[dict[str, str]]] = {
        mote: []
        for mote in MOTES
    }

    seen: dict[str, str] = {}

    for item in evidence:
        if not isinstance(item, Mapping):
            raise GuiseScenarioError(
                "evidence item must be a mapping"
            )

        mote = required(
            item.get("mote"),
            "evidence mote",
        )
        identity = required(
            item.get("identity"),
            "evidence identity",
        )
        status = required(
            item.get("status"),
            "evidence status",
        )

        if mote not in MOTES:
            raise GuiseScenarioError(
                f"unknown evidence mote: {mote}"
            )

        if identity in seen:
            if seen[identity] != mote:
                raise GuiseScenarioError(
                    "evidence identity has conflicting mote assignments"
                )

            continue

        seen[identity] = mote

        indexed[mote].append(
            {
                "identity": identity,
                "status": status,
            }
        )

    for items in indexed.values():
        items.sort(
            key=lambda item: (
                item["identity"],
                item["status"],
            )
        )

    assessments = []

    for pressure in normalized["pressures"]:
        mote = pressure["mote"]

        assessments.append(
            {
                "mote": mote,
                "intensity": pressure["intensity"],
                "evidence": indexed[mote],
                "evidence_count": len(indexed[mote]),
            }
        )

    result = {
        "schema": SCHEMA,
        "scenario": normalized["identity"],
        "character": normalized["character"],
        "authoritative": False,
        "simulated": True,
        "assessments": assessments,
        "interpretation": "not_generated",
    }

    result["digest"] = digest(result)

    return result


def compare(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare scenario assessments without inferring character change."""

    if first.get("character") != second.get("character"):
        raise GuiseScenarioError(
            "cannot compare different characters"
        )

    if first.get("schema") != SCHEMA:
        raise GuiseScenarioError(
            "invalid first scenario projection"
        )

    if second.get("schema") != SCHEMA:
        raise GuiseScenarioError(
            "invalid second scenario projection"
        )

    left = first.get("assessments")
    right = second.get("assessments")

    if not isinstance(left, list) or not isinstance(right, list):
        raise GuiseScenarioError(
            "assessments must be lists"
        )

    return {
        "schema": SCHEMA,
        "character": first["character"],
        "authoritative": False,
        "first": first.get("scenario"),
        "second": second.get("scenario"),
        "identical_assessments": (
            canonical(left) == canonical(right)
        ),
        "first_digest": digest(left),
        "second_digest": digest(right),
    }
