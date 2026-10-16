#!/usr/bin/env python3

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping


schema = (
    "savant://runtime/envoy/"
    "orobouros-promotion-gate/1.0.0"
)

owner = "exile:envoy"
persona_id = "orobouros"

verification_owner = "notary"
mutation_owner = "coda"

authority_effect = "none"


class orobouros_promotion_gate_error(
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
            orobouros_promotion_gate_error(
                f"{label} is required"
            )
        )

    return normalized


def _admission_projection(
    admission: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    value = _mapping(
        admission
    )

    admitted = bool(
        value.get(
            "admitted",
            False,
        )
    )

    owner_value = str(
        value.get(
            "owner"
        )
        or value.get(
            "verifier_owner"
        )
        or ""
    ).strip()

    admission_ref = str(
        value.get(
            "admission_ref"
        )
        or value.get(
            "attestation_ref"
        )
        or value.get(
            "receipt_ref"
        )
        or ""
    ).strip()

    evidence_digest = str(
        value.get(
            "evidence_digest"
        )
        or value.get(
            "subject_digest"
        )
        or ""
    ).strip()

    return {
        "admitted":
            admitted,
        "owner":
            owner_value,
        "admission_ref":
            admission_ref,
        "evidence_digest":
            evidence_digest,
    }


def evaluate(
    *,
    registry_projection: Mapping[
        str,
        Any,
    ],
    shadow_evaluation: Mapping[
        str,
        Any,
    ],
    notary_admission: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    registry = _mapping(
        registry_projection
    )

    shadow = _mapping(
        shadow_evaluation
    )

    admission = (
        _admission_projection(
            notary_admission
        )
    )

    registry_digest = (
        _required_text(
            registry.get(
                "registry_digest"
            ),
            label="registry digest",
        )
    )

    shadow_digest = (
        _required_text(
            shadow.get(
                "shadow_digest"
            ),
            label="shadow digest",
        )
    )

    if (
        registry.get(
            "shadow_digest"
        )
        != shadow_digest
    ):
        raise (
            orobouros_promotion_gate_error(
                "registry shadow lineage mismatch"
            )
        )

    blockers: list[str] = []

    if (
        shadow.get(
            "recommendation"
        )
        != "eligible_for_authoritative_review"
    ):
        blockers.append(
            "shadow_not_eligible"
        )

    if not admission[
        "admitted"
    ]:
        blockers.append(
            "notary_admission_missing"
        )

    if (
        admission[
            "owner"
        ]
        != verification_owner
    ):
        blockers.append(
            "notary_owner_mismatch"
        )

    if not admission[
        "admission_ref"
    ]:
        blockers.append(
            "notary_admission_ref_missing"
        )

    subject_matches = (
        admission[
            "evidence_digest"
        ]
        in {
            shadow_digest,
            registry_digest,
        }
    )

    if not subject_matches:
        blockers.append(
            "notary_subject_mismatch"
        )

    champion = _mapping(
        registry.get(
            "champion"
        )
    )

    challenger = _mapping(
        registry.get(
            "challenger"
        )
    )

    semantic = {
        "persona_id":
            persona_id,
        "registry_digest":
            registry_digest,
        "shadow_digest":
            shadow_digest,
        "champion":
            champion,
        "challenger":
            challenger,
        "notary_admission":
            admission,
        "blockers":
            sorted(
                set(
                    blockers
                )
            ),
    }

    gate_digest = _digest(
        semantic
    )

    eligible = not blockers

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "gate_id":
            (
                "orogate_"
                + gate_digest[
                    :32
                ]
            ),
        "gate_digest":
            gate_digest,
        "semantic":
            semantic,
        "eligible_for_coda_mutation":
            eligible,
        "verification_owner":
            verification_owner,
        "mutation_owner":
            mutation_owner,
        "mutation_executed":
            False,
        "promotion_executed":
            False,
        "authority_effect":
            authority_effect,
    }


def mutation_request(
    gate: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    value = _mapping(
        gate
    )

    if not value.get(
        "eligible_for_coda_mutation",
        False,
    ):
        raise (
            orobouros_promotion_gate_error(
                "promotion gate is not eligible "
                "for Coda mutation"
            )
        )

    semantic = _mapping(
        value.get(
            "semantic"
        )
    )

    challenger = _mapping(
        semantic.get(
            "challenger"
        )
    )

    champion = _mapping(
        semantic.get(
            "champion"
        )
    )

    request_semantic = {
        "mutation_owner":
            mutation_owner,
        "persona_owner":
            owner,
        "persona_id":
            persona_id,
        "operation":
            "promote_living_trait_crown",
        "from_composition_digest":
            champion.get(
                "composition_digest"
            ),
        "to_composition_digest":
            challenger.get(
                "composition_digest"
            ),
        "to_active_traits":
            challenger.get(
                "active_traits",
                [],
            ),
        "gate_digest":
            value.get(
                "gate_digest"
            ),
        "reversible":
            True,
        "preserve_previous":
            True,
        "destructive":
            False,
    }

    request_digest = _digest(
        request_semantic
    )

    return {
        "schema":
            (
                "savant://runtime/envoy/"
                "orobouros-coda-mutation-request/1.0.0"
            ),
        "owner":
            owner,
        "target_owner":
            mutation_owner,
        "request_id":
            (
                "oromut_"
                + request_digest[
                    :32
                ]
            ),
        "request_digest":
            request_digest,
        "semantic":
            request_semantic,
        "authorized_by_envoy":
            True,
        "requires_coda_execution":
            True,
        "executed":
            False,
        "authority_effect":
            "none",
    }


def selftest() -> dict[str, Any]:
    registry = {
        "registry_digest":
            "registry-digest",
        "shadow_digest":
            "shadow-digest",
        "champion":
            {
                "composition_digest":
                    "champion-digest",
                "active_traits":
                    [
                        "analytical_rigor",
                    ],
            },
        "challenger":
            {
                "composition_digest":
                    "challenger-digest",
                "active_traits":
                    [
                        "analytical_rigor",
                        "planning",
                    ],
            },
    }

    shadow = {
        "shadow_digest":
            "shadow-digest",
        "recommendation":
            "eligible_for_authoritative_review",
    }

    admission = {
        "owner":
            "notary",
        "admitted":
            True,
        "admission_ref":
            "notary://attestation/example",
        "evidence_digest":
            "shadow-digest",
    }

    gate = evaluate(
        registry_projection=
            registry,
        shadow_evaluation=
            shadow,
        notary_admission=
            admission,
    )

    if not gate[
        "eligible_for_coda_mutation"
    ]:
        raise (
            orobouros_promotion_gate_error(
                "valid gate was rejected"
            )
        )

    request = mutation_request(
        gate
    )

    if request[
        "executed"
    ]:
        raise (
            orobouros_promotion_gate_error(
                "mutation request executed itself"
            )
        )

    if (
        request[
            "target_owner"
        ]
        != mutation_owner
    ):
        raise (
            orobouros_promotion_gate_error(
                "mutation ownership escaped Coda"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "gate_digest":
            gate[
                "gate_digest"
            ],
        "request_digest":
            request[
                "request_digest"
            ],
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
