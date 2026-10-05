#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


schema = (
    "savant://runtime/envoy/"
    "orobouros-evolution-registry/1.0.0"
)

owner = "exile:envoy"
persona_id = "orobouros"

verification_owner = "notary"
mutation_owner = "coda"
conversation_owner = "palaver"
execution_owner = "opus"

authority_effect = "none"


class orobouros_evolution_registry_error(
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


def _identifier(
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
            orobouros_evolution_registry_error(
                f"{label} is required"
            )
        )

    return normalized


def _tokens(
    values: Iterable[Any] | None,
) -> tuple[str, ...]:
    if values is None:
        return ()

    return tuple(
        sorted(
            {
                str(item)
                .strip()
                .lower()
                for item in values
                if str(
                    item
                    or ""
                ).strip()
            }
        )
    )


@dataclass(
    frozen=True
)
class candidate:
    role: str
    composition_digest: str
    active_traits: tuple[str, ...]
    receipt_digest: str

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "role":
                self.role,
            "composition_digest":
                self.composition_digest,
            "active_traits":
                list(
                    self.active_traits
                ),
            "receipt_digest":
                self.receipt_digest,
        }


def candidate_from_receipt(
    *,
    role: str,
    receipt: Mapping[
        str,
        Any,
    ],
) -> candidate:
    normalized_role = (
        _identifier(
            role,
            label="candidate role",
        )
        .lower()
    )

    if normalized_role not in {
        "champion",
        "challenger",
    }:
        raise (
            orobouros_evolution_registry_error(
                "candidate role must be "
                "champion or challenger"
            )
        )

    value = _mapping(
        receipt
    )

    composition_digest = (
        _identifier(
            value.get(
                "composition_digest"
            ),
            label=
                "composition digest",
        )
    )

    traits = _tokens(
        value.get(
            "active_traits",
            (),
        )
    )

    receipt_digest = _digest(
        value
    )

    return candidate(
        role=
            normalized_role,
        composition_digest=
            composition_digest,
        active_traits=
            traits,
        receipt_digest=
            receipt_digest,
    )


def register_pair(
    *,
    champion_receipt: Mapping[
        str,
        Any,
    ],
    challenger_receipt: Mapping[
        str,
        Any,
    ],
    shadow_evaluation: Mapping[
        str,
        Any,
    ],
    evidence_refs: Iterable[Any] = (),
) -> dict[str, Any]:
    champion = (
        candidate_from_receipt(
            role="champion",
            receipt=
                champion_receipt,
        )
    )

    challenger = (
        candidate_from_receipt(
            role="challenger",
            receipt=
                challenger_receipt,
        )
    )

    if (
        champion.composition_digest
        == challenger.composition_digest
    ):
        raise (
            orobouros_evolution_registry_error(
                "champion and challenger "
                "must be distinct compositions"
            )
        )

    shadow = _mapping(
        shadow_evaluation
    )

    if (
        shadow.get(
            "owner"
        )
        != "exile:envoy"
    ):
        raise (
            orobouros_evolution_registry_error(
                "shadow evaluation must "
                "remain Envoy-owned"
            )
        )

    if not shadow.get(
        "shadow_only",
        False,
    ):
        raise (
            orobouros_evolution_registry_error(
                "shadow evaluation must "
                "remain non-mutating"
            )
        )

    shadow_digest = (
        _identifier(
            shadow.get(
                "shadow_digest"
            ),
            label="shadow digest",
        )
    )

    refs = _tokens(
        evidence_refs
    )

    semantic = {
        "persona_id":
            persona_id,
        "champion":
            champion.projection(),
        "challenger":
            challenger.projection(),
        "shadow_digest":
            shadow_digest,
        "shadow_recommendation":
            str(
                shadow.get(
                    "recommendation",
                    ""
                )
            ),
        "evidence_refs":
            list(
                refs
            ),
    }

    registry_digest = _digest(
        semantic
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "registry_id":
            (
                "oroevo_"
                + registry_digest[
                    :32
                ]
            ),
        "registry_digest":
            registry_digest,
        "semantic":
            semantic,
        "champion":
            champion.projection(),
        "challenger":
            challenger.projection(),
        "shadow_digest":
            shadow_digest,
        "shadow_recommendation":
            str(
                shadow.get(
                    "recommendation",
                    ""
                )
            ),
        "evidence_refs":
            list(
                refs
            ),
        "promotion_executed":
            False,
        "mutation_permission":
            False,
        "verification_owner":
            verification_owner,
        "mutation_owner":
            mutation_owner,
        "conversation_owner":
            conversation_owner,
        "execution_owner":
            execution_owner,
        "projection_only":
            True,
        "authority_effect":
            authority_effect,
    }


def replay_equivalent(
    left: Mapping[
        str,
        Any,
    ],
    right: Mapping[
        str,
        Any,
    ],
) -> bool:
    return (
        str(
            left.get(
                "registry_digest",
                "",
            )
        )
        == str(
            right.get(
                "registry_digest",
                "",
            )
        )
    )


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            persona_id,
        "verification_owner":
            verification_owner,
        "mutation_owner":
            mutation_owner,
        "conversation_owner":
            conversation_owner,
        "execution_owner":
            execution_owner,
        "projection_only":
            True,
        "mutation_permission":
            False,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    champion = {
        "composition_digest":
            "champion-digest",
        "active_traits":
            [
                "analytical_rigor",
            ],
    }

    challenger = {
        "composition_digest":
            "challenger-digest",
        "active_traits":
            [
                "analytical_rigor",
                "planning",
            ],
    }

    shadow = {
        "owner":
            "exile:envoy",
        "shadow_only":
            True,
        "shadow_digest":
            "shadow-digest",
        "recommendation":
            "eligible_for_authoritative_review",
    }

    first = register_pair(
        champion_receipt=
            champion,
        challenger_receipt=
            challenger,
        shadow_evaluation=
            shadow,
        evidence_refs=[
            "evidence-a",
            "evidence-b",
        ],
    )

    second = register_pair(
        champion_receipt=
            champion,
        challenger_receipt=
            challenger,
        shadow_evaluation=
            shadow,
        evidence_refs=[
            "evidence-b",
            "evidence-a",
        ],
    )

    if not replay_equivalent(
        first,
        second,
    ):
        raise (
            orobouros_evolution_registry_error(
                "registry replay failed"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "registry_digest":
            first[
                "registry_digest"
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
