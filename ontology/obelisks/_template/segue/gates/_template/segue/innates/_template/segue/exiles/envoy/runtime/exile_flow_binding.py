from __future__ import annotations

from typing import Any, Mapping

from .orobouros_evolution_registry import (
    authority_effect,
    conversation_owner,
    execution_owner,
    mutation_owner,
    owner,
    persona_id,
    register_pair,
    replay_equivalent,
    schema as registry_schema,
    status as registry_status,
    verification_owner,
)

from ...segue.exile_runtime.runtime.execution.exile_flow import (
    flow_contract,
    prepare_exile,
)


schema = "savant://runtime/envoy/exile-flow-binding/1.0.0"

capability_register_pair = (
    "exile:envoy:orobouros-register-pair"
)

capability_registry_status = (
    "exile:envoy:orobouros-registry-status"
)


def contracts() -> tuple[flow_contract, ...]:
    return (
        flow_contract(
            capability=
                capability_register_pair,
            source="exile:envoy",
            target="exile:envoy",
            accepted_schemas=(
                registry_schema,
            ),
            emitted_schema=
                registry_schema,
            idempotent=True,
            replayable=True,
        ),
        flow_contract(
            capability=
                capability_registry_status,
            source="exile:envoy",
            target="exile:envoy",
            accepted_schemas=(
                registry_schema,
            ),
            emitted_schema=
                registry_schema,
            idempotent=True,
            replayable=True,
        ),
    )


def register_pair_handler(
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    champion = payload.get(
        "champion_receipt"
    )

    challenger = payload.get(
        "challenger_receipt"
    )

    shadow = payload.get(
        "shadow_evaluation"
    )

    if not isinstance(
        champion,
        Mapping,
    ):
        raise ValueError(
            "champion_receipt is required"
        )

    if not isinstance(
        challenger,
        Mapping,
    ):
        raise ValueError(
            "challenger_receipt is required"
        )

    if not isinstance(
        shadow,
        Mapping,
    ):
        raise ValueError(
            "shadow_evaluation is required"
        )

    evidence_refs = payload.get(
        "evidence_refs",
        (),
    )

    return register_pair(
        champion_receipt=
            champion,
        challenger_receipt=
            challenger,
        shadow_evaluation=
            shadow,
        evidence_refs=
            evidence_refs,
    )


def registry_status_handler(
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    del payload

    return registry_status()


def handler_for(
    capability: str,
):
    handlers = {
        capability_register_pair:
            register_pair_handler,
        capability_registry_status:
            registry_status_handler,
    }

    try:
        return handlers[
            str(
                capability
            ).strip().lower()
        ]
    except KeyError as exc:
        raise ValueError(
            "unsupported envoy flow capability"
        ) from exc


def preparation() -> dict[str, Any]:
    return prepare_exile(
        exile=owner,
        capabilities=(
            capability_register_pair,
            capability_registry_status,
        ),
        accepts=(
            registry_schema,
        ),
        emits=(
            registry_schema,
        ),
        extensions={
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
            "authority_effect":
                authority_effect,
            "registry":
                registry_schema,
        },
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
        "authority_effect":
            authority_effect,
        "registry_schema":
            registry_schema,
        "capabilities": [
            contract.capability
            for contract in contracts()
        ],
        "flow_owner":
            "exile:segue",
        "creates_authority":
            False,
        "changes_ownership":
            False,
    }


def selftest() -> dict[str, Any]:
    champion = {
        "composition_digest":
            "flow-champion",
        "active_traits": [
            "analytical_rigor",
        ],
    }

    challenger = {
        "composition_digest":
            "flow-challenger",
        "active_traits": [
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
            "flow-shadow",
        "recommendation":
            "eligible_for_authoritative_review",
    }

    first = register_pair_handler(
        {
            "champion_receipt":
                champion,
            "challenger_receipt":
                challenger,
            "shadow_evaluation":
                shadow,
            "evidence_refs": [
                "evidence-a",
                "evidence-b",
            ],
        }
    )

    second = register_pair_handler(
        {
            "champion_receipt":
                champion,
            "challenger_receipt":
                challenger,
            "shadow_evaluation":
                shadow,
            "evidence_refs": [
                "evidence-b",
                "evidence-a",
            ],
        }
    )

    prepared = preparation()

    checks = {
        "owner_preserved":
            owner == "exile:envoy",
        "verification_owner_preserved":
            verification_owner
            == "notary",
        "mutation_owner_preserved":
            mutation_owner
            == "coda",
        "conversation_owner_preserved":
            conversation_owner
            == "palaver",
        "execution_owner_preserved":
            execution_owner
            == "opus",
        "authority_effect_preserved":
            authority_effect
            == "none",
        "two_contracts":
            len(
                contracts()
            )
            == 2,
        "registry_replay_preserved":
            replay_equivalent(
                first,
                second,
            ),
        "promotion_not_executed":
            not bool(
                first.get(
                    "promotion_executed"
                )
            ),
        "mutation_not_permitted":
            not bool(
                first.get(
                    "mutation_permission"
                )
            ),
        "prepared_without_authority":
            not bool(
                prepared[
                    "boundaries"
                ][
                    "creates_authority"
                ]
            ),
    }

    return {
        "schema":
            schema,
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "status":
            status(),
    }


__all__ = [
    "capability_register_pair",
    "capability_registry_status",
    "contracts",
    "handler_for",
    "preparation",
    "schema",
    "selftest",
    "status",
]


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
