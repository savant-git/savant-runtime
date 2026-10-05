#!/usr/bin/env python3

from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence


schema = (
    "savant://runtime/envoy/"
    "orobouros-trait-promotion/1.0.0"
)

owner = "exile:envoy"
persona_id = "orobouros"

verification_owner = "exile:notary"
persistence_owner = "coda"

authority_effect = "none"

root = Path(
    "/root/savant-runtime"
)

envoy_runtime = (
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
)

adjudication_path = (
    envoy_runtime
    / "trait_adjudication.py"
)

persistence_path = (
    envoy_runtime
    / "trait_persistence.py"
)


class orobouros_trait_promotion_error(
    RuntimeError
):
    pass


def _canonical_json(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )


def _digest(
    value: Any,
) -> str:
    return sha256(
        _canonical_json(
            value
        )
    ).hexdigest()


def _mapping(
    value: Any,
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise (
            orobouros_trait_promotion_error(
                f"{label} must be a mapping"
            )
        )

    return {
        str(key):
            item
        for key, item
        in value.items()
    }


def _required_text(
    value: Any,
    *,
    label: str,
) -> str:
    normalized = str(
        value
        or ""
    ).strip()

    if not normalized:
        raise (
            orobouros_trait_promotion_error(
                f"{label} is required"
            )
        )

    return normalized


def _term(
    value: Any,
) -> str:
    return (
        str(
            value
            or ""
        )
        .strip()
        .lower()
        .replace(
            "-",
            "_",
        )
        .replace(
            " ",
            "_",
        )
    )


def _tokens(
    values: Any,
) -> tuple[str, ...]:
    if values is None:
        return ()

    if not isinstance(
        values,
        (
            list,
            tuple,
            set,
        ),
    ):
        raise (
            orobouros_trait_promotion_error(
                "token collection must be iterable"
            )
        )

    return tuple(
        sorted(
            {
                str(item)
                .strip()
                for item in values
                if str(
                    item
                    or ""
                ).strip()
            }
        )
    )


def _module(
    *,
    name: str,
    path: Path,
) -> ModuleType:
    if not path.is_file():
        raise (
            orobouros_trait_promotion_error(
                f"required runtime missing: {path}"
            )
        )

    specification = (
        importlib.util
        .spec_from_file_location(
            name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise (
            orobouros_trait_promotion_error(
                f"unable to load runtime: {path}"
            )
        )

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    specification.loader.exec_module(
        module
    )

    return module


def adjudication_runtime() -> ModuleType:
    return _module(
        name=(
            "savant_envoy_"
            "trait_adjudication"
        ),
        path=
            adjudication_path,
    )


def persistence_runtime() -> ModuleType:
    return _module(
        name=(
            "savant_envoy_"
            "trait_persistence"
        ),
        path=
            persistence_path,
    )


def _validate_evolution(
    evolution_projection: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    evolution = _mapping(
        evolution_projection,
        label="evolution_projection",
    )

    if (
        evolution.get(
            "owner"
        )
        != owner
    ):
        raise (
            orobouros_trait_promotion_error(
                "evolution must remain Envoy-owned"
            )
        )

    if (
        evolution.get(
            "persona_id"
        )
        != persona_id
    ):
        raise (
            orobouros_trait_promotion_error(
                "invalid persona identity"
            )
        )

    gate = _mapping(
        evolution.get(
            "promotion_gate"
        ),
        label="promotion_gate",
    )

    request = _mapping(
        evolution.get(
            "coda_mutation_request"
        ),
        label="coda_mutation_request",
    )

    registry = _mapping(
        evolution.get(
            "registry"
        ),
        label="registry",
    )

    shadow = _mapping(
        evolution.get(
            "shadow"
        ),
        label="shadow",
    )

    if not gate.get(
        "eligible_for_coda_mutation",
        False,
    ):
        raise (
            orobouros_trait_promotion_error(
                "evolution has not passed promotion gate"
            )
        )

    if (
        request.get(
            "target_owner"
        )
        != persistence_owner
    ):
        raise (
            orobouros_trait_promotion_error(
                "mutation request must target Coda"
            )
        )

    if request.get(
        "executed"
    ):
        raise (
            orobouros_trait_promotion_error(
                "mutation request already claims execution"
            )
        )

    request_semantic = _mapping(
        request.get(
            "semantic"
        ),
        label="mutation request semantic",
    )

    gate_digest = _required_text(
        gate.get(
            "gate_digest"
        ),
        label="gate_digest",
    )

    if (
        request_semantic.get(
            "gate_digest"
        )
        != gate_digest
    ):
        raise (
            orobouros_trait_promotion_error(
                "mutation request gate lineage mismatch"
            )
        )

    if (
        registry.get(
            "shadow_digest"
        )
        != shadow.get(
            "shadow_digest"
        )
    ):
        raise (
            orobouros_trait_promotion_error(
                "shadow lineage mismatch"
            )
        )

    return {
        "evolution":
            evolution,
        "gate":
            gate,
        "request":
            request,
        "registry":
            registry,
        "shadow":
            shadow,
        "request_semantic":
            request_semantic,
    }


def _candidate(
    adjudication: ModuleType,
    *,
    trait_id: str,
    candidate_id: str,
    measurements: Mapping[
        str,
        Any,
    ],
    evidence_ids: Sequence[str],
    lineage: Sequence[str],
):
    return (
        adjudication
        .AdjudicationCandidate(
            candidate_id=
                candidate_id,
            trait_id=
                trait_id,
            measurements=tuple(
                measurements.items()
            ),
            evidence_ids=tuple(
                evidence_ids
            ),
            verified=True,
            evidence_admitted=True,
            lineage=tuple(
                lineage
            ),
        )
    )


def _policy(
    adjudication: ModuleType,
    *,
    policy_id: str,
    weights: Mapping[
        str,
        Any,
    ],
    minimum_margin: float,
):
    return (
        adjudication
        .AdjudicationPolicy(
            policy_id=
                policy_id,
            weights=tuple(
                weights.items()
            ),
            minimum_margin=
                minimum_margin,
            minimum_dimensions=1,
        )
    )


def _trial(
    value: Any,
    *,
    trait_id: str,
) -> dict[str, Any]:
    trial = _mapping(
        value,
        label=(
            f"trait trial {trait_id}"
        ),
    )

    champion = _mapping(
        trial.get(
            "champion"
        ),
        label=(
            f"{trait_id} champion"
        ),
    )

    challenger = _mapping(
        trial.get(
            "challenger"
        ),
        label=(
            f"{trait_id} challenger"
        ),
    )

    policy = _mapping(
        trial.get(
            "policy"
        ),
        label=(
            f"{trait_id} policy"
        ),
    )

    admission = _mapping(
        trial.get(
            "notary_admission"
        ),
        label=(
            f"{trait_id} notary admission"
        ),
    )

    if not admission.get(
        "admitted",
        False,
    ):
        raise (
            orobouros_trait_promotion_error(
                f"{trait_id} evidence is not admitted"
            )
        )

    admission_owner = str(
        admission.get(
            "owner"
        )
        or admission.get(
            "verifier_owner"
        )
        or ""
    ).strip()

    if (
        admission_owner
        not in {
            "notary",
            verification_owner,
        }
    ):
        raise (
            orobouros_trait_promotion_error(
                f"{trait_id} admission owner is not Notary"
            )
        )

    admission_ref = (
        _required_text(
            admission.get(
                "admission_ref"
            )
            or admission.get(
                "attestation_ref"
            ),
            label=(
                f"{trait_id} admission_ref"
            ),
        )
    )

    champion_measurements = (
        _mapping(
            champion.get(
                "measurements"
            ),
            label=(
                f"{trait_id} champion measurements"
            ),
        )
    )

    challenger_measurements = (
        _mapping(
            challenger.get(
                "measurements"
            ),
            label=(
                f"{trait_id} challenger measurements"
            ),
        )
    )

    weights = _mapping(
        policy.get(
            "weights"
        ),
        label=(
            f"{trait_id} policy weights"
        ),
    )

    if not champion_measurements:
        raise (
            orobouros_trait_promotion_error(
                f"{trait_id} champion measurements are empty"
            )
        )

    if not challenger_measurements:
        raise (
            orobouros_trait_promotion_error(
                f"{trait_id} challenger measurements are empty"
            )
        )

    if not weights:
        raise (
            orobouros_trait_promotion_error(
                f"{trait_id} policy weights are empty"
            )
        )

    evidence_ids = _tokens(
        trial.get(
            "evidence_ids"
        )
    )

    if not evidence_ids:
        evidence_ids = (
            admission_ref,
        )

    return {
        "champion":
            champion,
        "challenger":
            challenger,
        "policy":
            policy,
        "admission_ref":
            admission_ref,
        "evidence_ids":
            evidence_ids,
        "champion_measurements":
            champion_measurements,
        "challenger_measurements":
            challenger_measurements,
        "weights":
            weights,
    }


def project(
    *,
    evolution_projection: Mapping[
        str,
        Any,
    ],
    trait_trials: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    validated = (
        _validate_evolution(
            evolution_projection
        )
    )

    trials = _mapping(
        trait_trials,
        label="trait_trials",
    )

    if not trials:
        raise (
            orobouros_trait_promotion_error(
                "trait_trials must not be empty"
            )
        )

    adjudication = (
        adjudication_runtime()
    )

    request_semantic = (
        validated[
            "request_semantic"
        ]
    )

    registry = validated[
        "registry"
    ]

    champion_registry = _mapping(
        registry.get(
            "champion"
        ),
        label="registry champion",
    )

    challenger_registry = _mapping(
        registry.get(
            "challenger"
        ),
        label="registry challenger",
    )

    champion_composition = (
        _required_text(
            request_semantic.get(
                "from_composition_digest"
            ),
            label="from_composition_digest",
        )
    )

    challenger_composition = (
        _required_text(
            request_semantic.get(
                "to_composition_digest"
            ),
            label="to_composition_digest",
        )
    )

    target_traits = {
        _term(
            item
        )
        for item in (
            request_semantic.get(
                "to_active_traits"
            )
            or ()
        )
        if _term(
            item
        )
    }

    decisions: list[
        dict[str, Any]
    ] = []

    for raw_trait_id in sorted(
        trials
    ):
        trait_id = _term(
            raw_trait_id
        )

        if not trait_id:
            raise (
                orobouros_trait_promotion_error(
                    "trait identity is required"
                )
            )

        row = _trial(
            trials[
                raw_trait_id
            ],
            trait_id=
                trait_id,
        )

        champion = row[
            "champion"
        ]

        challenger = row[
            "challenger"
        ]

        previous_champion_id = (
            _required_text(
                champion.get(
                    "candidate_id"
                ),
                label=(
                    f"{trait_id} champion candidate_id"
                ),
            )
        )

        challenger_id = (
            _required_text(
                challenger.get(
                    "candidate_id"
                ),
                label=(
                    f"{trait_id} challenger candidate_id"
                ),
            )
        )

        if (
            previous_champion_id
            == challenger_id
        ):
            raise (
                orobouros_trait_promotion_error(
                    f"{trait_id} champion and challenger identities match"
                )
            )

        evidence_ids = tuple(
            sorted(
                set(
                    row[
                        "evidence_ids"
                    ]
                    + (
                        row[
                            "admission_ref"
                        ],
                    )
                )
            )
        )

        lineage = tuple(
            sorted(
                {
                    champion_composition,
                    challenger_composition,
                    _required_text(
                        validated[
                            "shadow"
                        ].get(
                            "shadow_digest"
                        ),
                        label="shadow_digest",
                    ),
                    _required_text(
                        validated[
                            "gate"
                        ].get(
                            "gate_digest"
                        ),
                        label="gate_digest",
                    ),
                    _required_text(
                        validated[
                            "request"
                        ].get(
                            "request_digest"
                        ),
                        label="request_digest",
                    ),
                }
            )
        )

        champion_candidate = (
            _candidate(
                adjudication,
                trait_id=
                    trait_id,
                candidate_id=
                    previous_champion_id,
                measurements=
                    row[
                        "champion_measurements"
                    ],
                evidence_ids=
                    evidence_ids,
                lineage=
                    lineage,
            )
        )

        challenger_candidate = (
            _candidate(
                adjudication,
                trait_id=
                    trait_id,
                candidate_id=
                    challenger_id,
                measurements=
                    row[
                        "challenger_measurements"
                    ],
                evidence_ids=
                    evidence_ids,
                lineage=
                    lineage,
            )
        )

        policy_id = (
            _term(
                row[
                    "policy"
                ].get(
                    "policy_id"
                )
            )
            or (
                "orobouros_"
                "evidence_driven_"
                "trait_promotion_v1"
            )
        )

        policy = _policy(
            adjudication,
            policy_id=
                policy_id,
            weights=
                row[
                    "weights"
                ],
            minimum_margin=float(
                row[
                    "policy"
                ].get(
                    "minimum_margin",
                    0.03,
                )
            ),
        )

        decision = (
            adjudication.adjudicate(
                (
                    champion_candidate,
                    challenger_candidate,
                ),
                policy,
                previous_champion_id=
                    previous_champion_id,
            )
        )

        decision_projection = (
            decision.projection()
        )

        winner = (
            decision_projection.get(
                "winner_candidate_id"
            )
        )

        decision_name = (
            decision_projection.get(
                "decision"
            )
        )

        if trait_id in target_traits:
            compatible = (
                decision_name
                in {
                    "challenge_wins",
                    "retain_champion",
                }
            )
        else:
            compatible = (
                decision_name
                in {
                    "retain_champion",
                    "no_decision",
                }
            )

        decisions.append(
            {
                "trait_id":
                    trait_id,
                "target_active":
                    (
                        trait_id
                        in target_traits
                    ),
                "previous_champion_id":
                    previous_champion_id,
                "challenger_candidate_id":
                    challenger_id,
                "winner_candidate_id":
                    winner,
                "decision":
                    decision_name,
                "compatible_with_whole_crown_target":
                    compatible,
                "notary_admission_ref":
                    row[
                        "admission_ref"
                    ],
                "adjudication":
                    decision_projection,
            }
        )

    incompatible = [
        row[
            "trait_id"
        ]
        for row in decisions
        if not row[
            "compatible_with_whole_crown_target"
        ]
    ]

    semantic = {
        "persona_id":
            persona_id,
        "from_composition_digest":
            champion_composition,
        "to_composition_digest":
            challenger_composition,
        "target_active_traits":
            sorted(
                target_traits
            ),
        "registry_champion_digest":
            champion_registry.get(
                "composition_digest"
            ),
        "registry_challenger_digest":
            challenger_registry.get(
                "composition_digest"
            ),
        "decisions":
            decisions,
        "incompatible_traits":
            sorted(
                incompatible
            ),
    }

    projection_digest = (
        _digest(
            semantic
        )
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "projection_id":
            (
                "orotraits_"
                + projection_digest[
                    :32
                ]
            ),
        "projection_digest":
            projection_digest,
        "semantic":
            semantic,
        "decisions":
            decisions,
        "decision_count":
            len(
                decisions
            ),
        "whole_crown_eligible":
            not incompatible,
        "incompatible_traits":
            sorted(
                incompatible
            ),
        "verification_owner":
            verification_owner,
        "persistence_owner":
            persistence_owner,
        "persistence_executed":
            False,
        "crown_mutated":
            False,
        "baseline_mutated":
            False,
        "trait_pool_mutated":
            False,
        "authoritative":
            False,
        "authority_effect":
            authority_effect,
    }


def persist(
    promotion_projection: Mapping[
        str,
        Any,
    ],
    *,
    expected_digest: str | None = None,
) -> dict[str, Any]:
    projection = _mapping(
        promotion_projection,
        label="promotion_projection",
    )

    if (
        projection.get(
            "owner"
        )
        != owner
    ):
        raise (
            orobouros_trait_promotion_error(
                "promotion projection must remain Envoy-owned"
            )
        )

    if not projection.get(
        "whole_crown_eligible",
        False,
    ):
        raise (
            orobouros_trait_promotion_error(
                "whole Crown promotion is not eligible"
            )
        )

    rows = projection.get(
        "decisions"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise (
            orobouros_trait_promotion_error(
                "promotion decisions must be a list"
            )
        )

    persistence = (
        persistence_runtime()
    )

    initial_digest = (
        persistence.current_digest()
    )

    if (
        expected_digest is not None
        and expected_digest
        != initial_digest
    ):
        raise (
            orobouros_trait_promotion_error(
                "trait history changed since inspection"
            )
        )

    current_digest = (
        initial_digest
    )

    persisted: list[
        dict[str, Any]
    ] = []

    for row in rows:
        decision = _mapping(
            row,
            label="promotion decision",
        )

        adjudication = _mapping(
            decision.get(
                "adjudication"
            ),
            label="adjudication",
        )

        result = (
            persistence.append_decision(
                adjudication,
                expected_digest=
                    current_digest,
                requester="envoy",
            )
        )

        persisted.append(
            result
        )

        current_digest = (
            persistence.current_digest()
        )

    return {
        "schema":
            (
                "savant://runtime/envoy/"
                "orobouros-trait-promotion-"
                "persistence/1.0.0"
            ),
        "owner":
            owner,
        "persona_id":
            persona_id,
        "persistence_owner":
            persistence_owner,
        "projection_digest":
            projection.get(
                "projection_digest"
            ),
        "decision_count":
            len(
                rows
            ),
        "persisted_count":
            len(
                persisted
            ),
        "initial_store_digest":
            initial_digest,
        "final_store_digest":
            current_digest,
        "results":
            persisted,
        "coda_executed_mutation":
            True,
        "envoy_executed_mutation":
            False,
        "baseline_mutated":
            False,
        "trait_pool_mutated":
            False,
        "history_append_only":
            True,
        "authoritative":
            False,
        "authority_effect":
            authority_effect,
    }


def status() -> dict[str, Any]:
    adjudication = (
        adjudication_runtime()
    )

    persistence = (
        persistence_runtime()
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "verification_owner":
            verification_owner,
        "persistence_owner":
            persistence_owner,
        "native_adjudication":
            adjudication.status(),
        "native_persistence":
            persistence.status(),
        "whole_crown_projection":
            True,
        "per_trait_adjudication":
            True,
        "verified_admitted_evidence_required":
            True,
        "optimistic_concurrency":
            True,
        "append_only_history":
            True,
        "automatic_promotion":
            False,
        "baseline_mutation":
            False,
        "trait_pool_mutation":
            False,
        "authoritative":
            False,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    adjudication = (
        adjudication_runtime()
    )

    persistence = (
        persistence_runtime()
    )

    adjudication_status = (
        adjudication.status()
    )

    persistence_status = (
        persistence.selftest()
    )

    if (
        adjudication_status.get(
            "owner"
        )
        != owner
    ):
        raise (
            orobouros_trait_promotion_error(
                "native adjudication ownership mismatch"
            )
        )

    if (
        persistence_status.get(
            "persistence_owner"
        )
        != persistence_owner
    ):
        raise (
            orobouros_trait_promotion_error(
                "native persistence ownership mismatch"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "owner":
            owner,
        "verification_owner":
            verification_owner,
        "persistence_owner":
            persistence_owner,
        "native_trait_adjudication":
            True,
        "native_trait_persistence":
            True,
        "mutation_performed":
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
            default=str,
        )
    )
