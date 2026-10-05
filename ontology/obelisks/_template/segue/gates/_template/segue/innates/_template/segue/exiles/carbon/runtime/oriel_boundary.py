#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json

from pathlib import Path
from typing import Any, Mapping


owner = "carbon"
component = "oriel-boundary"
authority_effect = "none"
schema = "savant.carbon.oriel-boundary.v1"

carbon_root = (
    Path(__file__).resolve().parent.parent
)


class oriel_boundary_error(
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
        raise oriel_boundary_error(
            (
                "cannot read "
                + relative_path
                + ": "
                + str(exc)
            )
        ) from exc

    except json.JSONDecodeError as exc:
        raise oriel_boundary_error(
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
        raise oriel_boundary_error(
            (
                "expected json object: "
                + relative_path
            )
        )

    return value


def projection() -> dict[str, Any]:
    entity = load_json(
        "entity.json"
    )

    authority = load_json(
        "authority/authority.json"
    )

    segue = load_json(
        "segue/entity.json"
    )

    edges = load_json(
        "segue/graph/edges.json"
    )

    inheritance = load_json(
        "segue/lineage/inheritance.json"
    )

    specialization = next(
        (
            value
            for value
            in entity.get(
                "specializations",
                [],
            )
            if (
                isinstance(
                    value,
                    Mapping,
                )
                and value.get(
                    "id"
                )
                == "carbon.oriel"
            )
        ),
        None,
    )

    edge_rows = [
        value
        for value
        in edges.get(
            "edges",
            [],
        )
        if isinstance(
            value,
            Mapping,
        )
    ]

    external_reality_edge = any(
        (
            value.get(
                "source"
            )
            == (
                "source:"
                "external_historical_reality"
            )
            and value.get(
                "target"
            )
            == (
                "exile:carbon/"
                "specialization:oriel"
            )
            and value.get(
                "binding"
            )
            == "reference"
            and value.get(
                "authority_transfer"
            )
            is False
        )
        for value
        in edge_rows
    )

    ownership_edge = any(
        (
            value.get(
                "source"
            )
            == "exile:carbon"
            and value.get(
                "target"
            )
            == (
                "exile:carbon/"
                "specialization:oriel"
            )
            and value.get(
                "relation"
            )
            == "owns_specialization"
        )
        for value
        in edge_rows
    )

    exports = {
        str(value)
        for value
        in segue.get(
            "exports",
            [],
        )
    }

    authority_map = authority.get(
        "authority",
        {},
    )

    classification = authority.get(
        "classification",
        {},
    )

    rules = authority.get(
        "rules",
        {},
    )

    identity_rules = inheritance.get(
        "identity_rules",
        {},
    )

    validation = {
        "carbon_identity_preserved":
            (
                entity.get(
                    "id"
                )
                == "carbon"
                and entity.get(
                    "graph_id"
                )
                == "exile:carbon"
            ),

        "oriel_contained_specialization":
            (
                isinstance(
                    specialization,
                    Mapping,
                )
                and specialization.get(
                    "graph_id"
                )
                == (
                    "exile:carbon/"
                    "specialization:oriel"
                )
                and specialization.get(
                    "owner"
                )
                == "carbon"
            ),

        "oriel_not_peer_exile":
            not (
                isinstance(
                    specialization,
                    Mapping,
                )
                and specialization.get(
                    "graph_id"
                )
                == "exile:oriel"
            ),

        "carbon_owns_oriel_execution":
            (
                authority_map.get(
                    "oriel_specialization"
                )
                == "carbon"
                and authority_map.get(
                    "oriel_chronology_logistics"
                )
                == "carbon"
            ),

        "quantum_remains_carbon_owned":
            (
                authority_map.get(
                    "quantum_simulation"
                )
                == "carbon"
            ),

        "causal_simulation_remains_carbon_owned":
            (
                authority_map.get(
                    "causal_simulation"
                )
                == "carbon"
            ),

        "historical_reality_remains_external":
            (
                authority_map.get(
                    "historical_reality"
                )
                == "external_source"
            ),

        "oriel_projection_remains_derived":
            (
                classification.get(
                    "oriel_projection"
                )
                == "derived_projection"
            ),

        "oriel_cannot_claim_history":
            (
                rules.get(
                    (
                        "carbon_may_claim_oriel_"
                        "projection_as_history"
                    )
                )
                is False
            ),

        "oriel_cannot_move_verified_anchor":
            (
                rules.get(
                    (
                        "oriel_may_move_verified_"
                        "historical_anchor"
                    )
                )
                is False
            ),

        "oriel_exports_present":
            {
                "oriel_specialization",
                "oriel_capability_surface",
                "oriel_projection_packet",
            }.issubset(
                exports
            ),

        "external_reality_reference_edge":
            external_reality_edge,

        "carbon_ownership_edge":
            ownership_edge,

        "historical_oriel_not_reactivated":
            (
                identity_rules.get(
                    (
                        "historical_oriel_is_"
                        "current_specialization"
                    )
                )
                is False
                and identity_rules.get(
                    "standalone_oriel_restored"
                )
                is False
            ),

        "authority_transfer":
            False,
    }

    result = {
        "schema":
            schema,

        "kind":
            "oriel-boundary-projection",

        "owner":
            owner,

        "component":
            component,

        "authority_effect":
            authority_effect,

        "validation":
            validation,

        "source_records": {
            "entity":
                clone(
                    entity
                ),

            "authority":
                clone(
                    authority
                ),

            "segue":
                clone(
                    segue
                ),

            "edges":
                clone(
                    edges
                ),

            "inheritance":
                clone(
                    inheritance
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

    validation = value[
        "validation"
    ]

    required = (
        "carbon_identity_preserved",
        "oriel_contained_specialization",
        "oriel_not_peer_exile",
        "carbon_owns_oriel_execution",
        "quantum_remains_carbon_owned",
        "causal_simulation_remains_carbon_owned",
        "historical_reality_remains_external",
        "oriel_projection_remains_derived",
        "oriel_cannot_claim_history",
        "oriel_cannot_move_verified_anchor",
        "oriel_exports_present",
        "external_reality_reference_edge",
        "carbon_ownership_edge",
        "historical_oriel_not_reactivated",
    )

    ready = all(
        bool(
            validation.get(
                key
            )
        )
        for key
        in required
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

        "ready":
            ready,

        "authority_transfer":
            False,
    }


def selftest() -> dict[str, Any]:
    value = projection()

    validation = value[
        "validation"
    ]

    failed = [
        key
        for key, state
        in validation.items()
        if (
            key
            != "authority_transfer"
            and state
            is not True
        )
    ]

    if failed:
        raise oriel_boundary_error(
            (
                "oriel boundary selftest "
                "failed: "
                + ", ".join(
                    sorted(
                        failed
                    )
                )
            )
        )

    if validation[
        "authority_transfer"
    ]:
        raise oriel_boundary_error(
            (
                "oriel boundary "
                "transferred authority"
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

        "carbon_identity_preserved":
            True,

        "oriel_contained_specialization":
            True,

        "quantum_remains_carbon_owned":
            True,

        "causal_simulation_remains_carbon_owned":
            True,

        "historical_reality_remains_external":
            True,

        "historical_oriel_not_reactivated":
            True,

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
