#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json

from pathlib import Path
from typing import Any, Mapping


owner = "carbon"
component = "oriel-lineage"
authority_effect = "none"
schema = "savant.carbon.oriel-lineage.v1"

carbon_root = (
    Path(
        __file__
    ).resolve().parent.parent
)


class oriel_lineage_error(
    RuntimeError
):
    pass


def clone(
    value: Any,
) -> Any:
    return copy.deepcopy(
        value
    )


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def load_json(
    relative_path: str,
) -> dict[str, Any]:
    path = (
        carbon_root
        / relative_path
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except OSError as exc:
        raise oriel_lineage_error(
            (
                "cannot read "
                + relative_path
                + ": "
                + str(
                    exc
                )
            )
        ) from exc

    except json.JSONDecodeError as exc:
        raise oriel_lineage_error(
            (
                "invalid json in "
                + relative_path
                + ": "
                + str(
                    exc
                )
            )
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise oriel_lineage_error(
            (
                "expected json object: "
                + relative_path
            )
        )

    return value


def projection() -> dict[str, Any]:
    historical = load_json(
        "lineage/oriel.json"
    )

    specialization = load_json(
        "lineage/oriel_specialization.json"
    )

    lineage = load_json(
        "lineage/lineage.json"
    )

    registry = load_json(
        "registry/manifests/oriel.json"
    )

    historical_rules = historical.get(
        "lineage_rules",
        {},
    )

    distinction = specialization.get(
        "identity_distinctions",
        {},
    )

    specialization_rules = specialization.get(
        "lineage_rules",
        {},
    )

    historical_valid = bool(
        historical.get(
            "id"
        )
        == "carbon.lineage.oriel"
        and historical.get(
            "relationship"
        )
        == "evolved_into"
        and isinstance(
            historical.get(
                "descendant"
            ),
            Mapping,
        )
        and historical[
            "descendant"
        ].get(
            "id"
        )
        == "carbon"
        and historical_rules.get(
            "carbon_supersedes_oriel_as_general_simulation_owner"
        )
        is True
    )

    specialization_valid = bool(
        specialization.get(
            "id"
        )
        == "carbon.lineage.oriel_specialization"
        and isinstance(
            specialization.get(
                "current_specialization"
            ),
            Mapping,
        )
        and specialization[
            "current_specialization"
        ].get(
            "id"
        )
        == "carbon.oriel"
        and specialization[
            "current_specialization"
        ].get(
            "owner"
        )
        == "carbon"
        and distinction.get(
            "historical_oriel_is_current_specialization"
        )
        is False
        and distinction.get(
            "standalone_oriel_runtime_restored"
        )
        is False
        and distinction.get(
            "current_oriel_specialization_is_carbon_owned"
        )
        is True
        and distinction.get(
            "carbon_remains_general_simulation_owner"
        )
        is True
        and specialization_rules.get(
            "ancestor_runtime_reactivated"
        )
        is False
    )

    artifact_index = {
        str(
            value.get(
                "id",
                "",
            )
        ):
            value
        for value
        in lineage.get(
            "artifacts",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    }

    projection_valid = bool(
        artifact_index.get(
            "oriel_ancestor",
            {},
        ).get(
            "record"
        )
        == "oriel.json"
        and artifact_index.get(
            "oriel_specialization",
            {},
        ).get(
            "record"
        )
        == "oriel_specialization.json"
    )

    registry_valid = bool(
        registry.get(
            "id"
        )
        == "carbon.oriel"
        and registry.get(
            "owner"
        )
        == "carbon"
        and registry.get(
            "authority_effect"
        )
        == "none"
    )

    result = {
        "schema":
            schema,

        "kind":
            "oriel-lineage-projection",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "historical_ancestor": {
            "identity":
                "oriel",

            "record":
                "lineage/oriel.json",

            "relationship":
                "evolved_into_carbon",

            "general_simulation_owner":
                False,

            "historical_identity_preserved":
                True,
        },

        "current_specialization": {
            "identity":
                "carbon.oriel",

            "display_name":
                "oriel",

            "record":
                (
                    "lineage/"
                    "oriel_specialization.json"
                ),

            "relationship":
                (
                    "carbon_specialization_"
                    "named_for_ancestor"
                ),

            "owner":
                "carbon",

            "general_simulation_owner":
                False,
        },

        "carbon": {
            "identity":
                "carbon",

            "general_simulation_owner":
                True,

            "quantum_owner":
                True,

            "causal_simulation_owner":
                True,
        },

        "validation": {
            "historical_lineage_valid":
                historical_valid,

            "specialization_lineage_valid":
                specialization_valid,

            "lineage_projection_valid":
                projection_valid,

            "registry_identity_valid":
                registry_valid,

            "historical_and_current_oriel_conflated":
                False,

            "standalone_oriel_restored":
                False,
        },

        "source_records": {
            "historical":
                clone(
                    historical
                ),

            "specialization":
                clone(
                    specialization
                ),

            "projection":
                clone(
                    lineage
                ),
        },

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "authority_transfer":
            False,
    }

    result[
        "digest"
    ] = digest(
        {
            key:
                value
            for key, value
            in result.items()
            if key
            != "digest"
        }
    )

    return result


def status() -> dict[str, Any]:
    value = projection()

    checks = value[
        "validation"
    ]

    ready = all(
        bool(
            checks.get(
                key
            )
        )
        for key
        in (
            "historical_lineage_valid",
            "specialization_lineage_valid",
            "lineage_projection_valid",
            "registry_identity_valid",
        )
    )

    return {
        "schema":
            schema,

        "kind":
            "status",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "historical_identity":
            "oriel",

        "current_specialization_identity":
            "carbon.oriel",

        "general_simulation_owner":
            "carbon",

        "standalone_oriel_restored":
            False,

        "historical_and_current_oriel_conflated":
            False,

        "authority_transfer":
            False,

        "ready":
            ready,
    }


def selftest() -> dict[str, Any]:
    value = projection()

    checks = value[
        "validation"
    ]

    failed = [
        key
        for key
        in (
            "historical_lineage_valid",
            "specialization_lineage_valid",
            "lineage_projection_valid",
            "registry_identity_valid",
        )
        if not checks.get(
            key
        )
    ]

    if failed:
        raise oriel_lineage_error(
            (
                "oriel lineage selftest failed: "
                + ", ".join(
                    failed
                )
            )
        )

    if checks.get(
        "historical_and_current_oriel_conflated"
    ):
        raise oriel_lineage_error(
            (
                "historical and current oriel "
                "identities were conflated"
            )
        )

    if checks.get(
        "standalone_oriel_restored"
    ):
        raise oriel_lineage_error(
            (
                "standalone historical oriel "
                "was incorrectly restored"
            )
        )

    return {
        "schema":
            schema,

        "kind":
            "selftest",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "ok":
            True,

        "historical_oriel_identity_preserved":
            True,

        "current_specialization_identity_distinct":
            True,

        "carbon_remains_general_simulation_owner":
            True,

        "standalone_oriel_restored":
            False,

        "authority_transfer":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",
    }


__all__ = [
    "projection",
    "selftest",
    "status",
]
