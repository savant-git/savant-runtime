#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


schema = (
    "savant://runtime/envoy/"
    "orobouros-shadow-evidence-compat/1.0.0"
)

owner = "exile:envoy"
persona_id = "orobouros"

canonical_evidence_owner = "exile:palaver"
legacy_evidence_owner = "palaver"

authority_effect = "none"


root = Path(
    "/root/savant-runtime"
)

shadow_path = (
    root
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "envoy"
    / "runtime"
    / "orobouros_shadow_evolution.py"
)


class orobouros_shadow_evidence_compat_error(
    RuntimeError
):
    pass


def _mapping(
    value: Any,
) -> dict[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        return {}

    return {
        str(key):
            item
        for key, item
        in value.items()
    }


def _load_shadow_runtime():
    if not shadow_path.is_file():
        raise (
            orobouros_shadow_evidence_compat_error(
                "Orobouros shadow evolution runtime "
                "is missing"
            )
        )

    specification = (
        importlib.util.spec_from_file_location(
            "savant_envoy_orobouros_shadow_evolution",
            shadow_path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise (
            orobouros_shadow_evidence_compat_error(
                "unable to load Orobouros shadow "
                "evolution runtime"
            )
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    specification.loader.exec_module(
        module
    )

    return module


def _normalize_evidence(
    evidence: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
) -> tuple[
    dict[str, Any],
    ...,
]:
    normalized: list[
        dict[str, Any]
    ] = []

    for raw in evidence:
        item = _mapping(
            raw
        )

        if not item:
            continue

        source_owner = str(
            item.get(
                "owner"
            )
            or ""
        ).strip()

        if source_owner not in {
            canonical_evidence_owner,
            legacy_evidence_owner,
        }:
            normalized.append(
                item
            )
            continue

        compatibility = dict(
            item
        )

        compatibility[
            "canonical_source_owner"
        ] = canonical_evidence_owner

        compatibility[
            "owner"
        ] = legacy_evidence_owner

        normalized.append(
            compatibility
        )

    return tuple(
        normalized
    )


def evaluate_shadow(
    *,
    accepted_receipt: Mapping[
        str,
        Any,
    ],
    challenger_receipt: Mapping[
        str,
        Any,
    ],
    accepted_evidence: Iterable[
        Mapping[
            str,
            Any,
        ]
    ] = (),
    challenger_evidence: Iterable[
        Mapping[
            str,
            Any,
        ]
    ] = (),
    minimum_samples: int = 5,
    minimum_quality_samples: int = 0,
    required_margin: float = 0.02,
    regression_tolerance: float = 0.01,
) -> dict[str, Any]:
    shadow = _load_shadow_runtime()

    result = shadow.evaluate_shadow(
        accepted_receipt=
            accepted_receipt,
        challenger_receipt=
            challenger_receipt,
        accepted_evidence=
            _normalize_evidence(
                accepted_evidence
            ),
        challenger_evidence=
            _normalize_evidence(
                challenger_evidence
            ),
        minimum_samples=
            minimum_samples,
        minimum_quality_samples=
            minimum_quality_samples,
        required_margin=
            required_margin,
        regression_tolerance=
            regression_tolerance,
    )

    if not isinstance(
        result,
        dict,
    ):
        raise (
            orobouros_shadow_evidence_compat_error(
                "shadow runtime returned "
                "invalid projection"
            )
        )

    projection = dict(
        result
    )

    projection[
        "canonical_evidence_owner"
    ] = canonical_evidence_owner

    projection[
        "legacy_evidence_owner_compatibility"
    ] = legacy_evidence_owner

    projection[
        "evidence_owner_normalization"
    ] = True

    projection[
        "authority_effect"
    ] = "none"

    return projection


def status() -> dict[str, Any]:
    shadow = _load_shadow_runtime()

    source_status = (
        shadow.status()
        if callable(
            getattr(
                shadow,
                "status",
                None,
            )
        )
        else {}
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "canonical_evidence_owner":
            canonical_evidence_owner,
        "legacy_evidence_owner":
            legacy_evidence_owner,
        "canonical_evidence_preserved":
            True,
        "legacy_boundary_only":
            True,
        "source_runtime":
            source_status,
        "mutation_permission":
            False,
        "promotion_permission":
            False,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    sample = {
        "owner":
            canonical_evidence_owner,
        "authority_effect":
            "none",
        "evidence_digest":
            "evidence-example",
        "semantic":
            {
                "operational_observation":
                    {
                        "success":
                            True,
                        "cancelled":
                            False,
                        "latency_ms":
                            100,
                        "retry_count":
                            0,
                        "provider_failover_count":
                            0,
                    },
                "external_evaluations":
                    [],
            },
    }

    normalized = (
        _normalize_evidence(
            [
                sample
            ]
        )
    )

    if (
        normalized[
            0
        ].get(
            "owner"
        )
        != legacy_evidence_owner
    ):
        raise (
            orobouros_shadow_evidence_compat_error(
                "legacy owner normalization failed"
            )
        )

    if (
        normalized[
            0
        ].get(
            "canonical_source_owner"
        )
        != canonical_evidence_owner
    ):
        raise (
            orobouros_shadow_evidence_compat_error(
                "canonical owner lineage was lost"
            )
        )

    if (
        sample[
            "owner"
        ]
        != canonical_evidence_owner
    ):
        raise (
            orobouros_shadow_evidence_compat_error(
                "source evidence was mutated"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "canonical_evidence_owner":
            canonical_evidence_owner,
        "legacy_boundary_only":
            True,
        "source_mutated":
            False,
        "authority_effect":
            authority_effect,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
