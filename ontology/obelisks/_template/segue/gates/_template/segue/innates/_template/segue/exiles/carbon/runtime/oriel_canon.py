#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


owner = "carbon"
component = "oriel-canon"
authority_effect = "none"
schema = "savant.carbon.oriel-canon.v1"

carbon_root = (
    Path(__file__).resolve().parent.parent
)


class oriel_canon_error(
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
        separators=(",", ":"),
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
        raise oriel_canon_error(
            (
                "cannot read "
                + relative_path
                + ": "
                + str(exc)
            )
        ) from exc

    except json.JSONDecodeError as exc:
        raise oriel_canon_error(
            (
                "invalid json in "
                + relative_path
                + ": "
                + str(exc)
            )
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise oriel_canon_error(
            (
                "expected json object: "
                + relative_path
            )
        )

    return value


def canon_policy() -> dict[str, Any]:
    return load_json(
        "canon/oriel.json"
    )


def validate_policy() -> dict[str, Any]:
    policy = canon_policy()

    authority = load_json(
        "authority/authority.json"
    )

    lineage = load_json(
        "lineage/oriel_specialization.json"
    )

    authority_map = authority.get(
        "authority",
        {},
    )

    classification = authority.get(
        "classification",
        {},
    )

    distinctions = lineage.get(
        "identity_distinctions",
        {},
    )

    identity = policy.get(
        "identity",
        {},
    )

    invariants = policy.get(
        "invariants",
        {},
    )

    checks = {
        "identity_is_carbon_oriel":
            (
                isinstance(
                    identity,
                    Mapping,
                )
                and identity.get(
                    "current"
                )
                == "carbon.oriel"
            ),

        "owner_is_carbon":
            policy.get(
                "owner"
            )
            == "carbon",

        "contained_by_carbon":
            policy.get(
                "container"
            )
            == "carbon.simulation",

        "authority_effect_none":
            policy.get(
                "authority_effect"
            )
            == "none",

        "carbon_owns_quantum":
            authority_map.get(
                "quantum_simulation"
            )
            == "carbon",

        "carbon_owns_causal_simulation":
            authority_map.get(
                "causal_simulation"
            )
            == "carbon",

        "historical_reality_external":
            authority_map.get(
                "historical_reality"
            )
            == "external_source",

        "oriel_projection_is_derived":
            classification.get(
                "oriel_projection"
            )
            == "derived_projection",

        "historical_oriel_distinct":
            distinctions.get(
                (
                    "historical_oriel_is_"
                    "current_specialization"
                )
            )
            is False,

        "standalone_oriel_not_restored":
            distinctions.get(
                "standalone_oriel_runtime_restored"
            )
            is False,

        "authority_transfer_disabled":
            invariants.get(
                "authority_transfer"
            )
            is False,
    }

    return {
        "schema":
            schema,

        "kind":
            "canon-policy-validation",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "checks":
            checks,

        "valid":
            all(
                checks.values()
            ),

        "source_state_mutated":
            False,
    }


def projection_guard(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    before = digest(
        packet
    )

    violations = []

    if (
        str(
            packet.get(
                "authority_effect",
                "none",
            )
        ).strip().lower()
        != "none"
    ):
        violations.append(
            "authority_effect"
        )

    if (
        str(
            packet.get(
                "canon_effect",
                "none",
            )
        ).strip().lower()
        != "none"
    ):
        violations.append(
            "canon_effect"
        )

    if (
        packet.get(
            "evidence_admission",
            False,
        )
        is not False
    ):
        violations.append(
            "evidence_admission"
        )

    if (
        packet.get(
            "authority_transfer",
            False,
        )
        is not False
    ):
        violations.append(
            "authority_transfer"
        )

    if (
        packet.get(
            "ownership_transfer",
            False,
        )
        is not False
    ):
        violations.append(
            "ownership_transfer"
        )

    if (
        packet.get(
            "interaction_claimed_as_fact",
            False,
        )
        is True
    ):
        violations.append(
            "interaction_claimed_as_fact"
        )

    if (
        packet.get(
            "reachability_claimed_as_occurrence",
            False,
        )
        is True
    ):
        violations.append(
            "reachability_claimed_as_occurrence"
        )

    if (
        packet.get(
            "simulation_claimed_as_observation",
            False,
        )
        is True
    ):
        violations.append(
            "simulation_claimed_as_observation"
        )

    if (
        packet.get(
            "quantum_collapse_promotes_canon",
            False,
        )
        is True
    ):
        violations.append(
            "quantum_collapse_promotes_canon"
        )

    after = digest(
        packet
    )

    if before != after:
        raise oriel_canon_error(
            "projection guard mutated input"
        )

    return {
        "schema":
            schema,

        "kind":
            "oriel-projection-canon-guard",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "accepted_as_oriel_projection":
            not violations,

        "promotion_allowed":
            False,

        "classification":
            "derived_projection",

        "violations":
            sorted(
                violations
            ),

        "source_digest":
            before,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",

        "evidence_admission":
            False,

        "authority_transfer":
            False,
    }


def status() -> dict[str, Any]:
    validation = validate_policy()

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

        "policy_valid":
            validation[
                "valid"
            ],

        "projection_self_promotion":
            False,

        "quantum_collapse_promotes_canon":
            False,

        "reachability_is_occurrence":
            False,

        "co_location_is_interaction":
            False,

        "authority_transfer":
            False,

        "ready":
            validation[
                "valid"
            ],
    }


def selftest() -> dict[str, Any]:
    validation = validate_policy()

    if not validation[
        "valid"
    ]:
        failed = sorted(
            key
            for key, value
            in validation[
                "checks"
            ].items()
            if not value
        )

        raise oriel_canon_error(
            (
                "canon policy validation failed: "
                + ", ".join(
                    failed
                )
            )
        )

    valid_packet = {
        "kind":
            "reachability-cone",

        "authority_effect":
            "none",

        "canon_effect":
            "none",

        "evidence_admission":
            False,

        "authority_transfer":
            False,

        "source_state_mutated":
            False,
    }

    allowed = projection_guard(
        valid_packet
    )

    if (
        not allowed[
            "accepted_as_oriel_projection"
        ]
        or allowed[
            "promotion_allowed"
        ]
    ):
        raise oriel_canon_error(
            (
                "valid derived projection "
                "guard failed"
            )
        )

    invalid_packet = {
        "kind":
            "quantum-collapse",

        "authority_effect":
            "none",

        "canon_effect":
            "promote",

        "evidence_admission":
            False,

        "quantum_collapse_promotes_canon":
            True,
    }

    rejected = projection_guard(
        invalid_packet
    )

    if rejected[
        "accepted_as_oriel_projection"
    ]:
        raise oriel_canon_error(
            (
                "invalid self-promoting "
                "projection was accepted"
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

        "canon_policy_valid":
            True,

        "derived_projection_accepted":
            True,

        "self_promoting_projection_rejected":
            True,

        "quantum_collapse_promotes_canon":
            False,

        "reachability_is_occurrence":
            False,

        "co_location_is_interaction":
            False,

        "authority_transfer":
            False,

        "source_state_mutated":
            False,

        "canon_effect":
            "none",
    }


__all__ = [
    "canon_policy",
    "projection_guard",
    "selftest",
    "status",
    "validate_policy",
]
