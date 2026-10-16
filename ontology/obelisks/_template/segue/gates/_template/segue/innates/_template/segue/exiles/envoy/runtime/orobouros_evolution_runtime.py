#!/usr/bin/env python3

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

try:
    from . import (
        orobouros_evolution_registry,
    )
    from . import (
        orobouros_promotion_gate,
    )
    from . import (
        orobouros_shadow_evolution,
    )
except ImportError:
    import orobouros_evolution_registry
    import orobouros_promotion_gate
    import orobouros_shadow_evolution


schema = (
    "savant://runtime/envoy/"
    "orobouros-evolution-runtime/1.0.0"
)

owner = "exile:envoy"

authority_effect = "none"


class orobouros_evolution_runtime_error(
    RuntimeError
):
    pass


def project(
    *,
    champion_receipt: Mapping[
        str,
        Any,
    ],
    challenger_receipt: Mapping[
        str,
        Any,
    ],
    champion_evidence: Iterable[
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
    notary_admission: Mapping[
        str,
        Any,
    ] | None = None,
    minimum_samples: int = 5,
    minimum_quality_samples: int = 0,
    required_margin: float = 0.02,
    regression_tolerance: float = 0.01,
) -> dict[str, Any]:
    shadow = (
        orobouros_shadow_evolution
        .evaluate_shadow(
            accepted_receipt=
                champion_receipt,
            challenger_receipt=
                challenger_receipt,
            accepted_evidence=
                champion_evidence,
            challenger_evidence=
                challenger_evidence,
            minimum_samples=
                minimum_samples,
            minimum_quality_samples=
                minimum_quality_samples,
            required_margin=
                required_margin,
            regression_tolerance=
                regression_tolerance,
        )
    )

    evidence_refs = tuple(
        sorted(
            {
                str(
                    item.get(
                        "evidence_digest",
                        "",
                    )
                )
                for item in (
                    tuple(
                        champion_evidence
                    )
                    + tuple(
                        challenger_evidence
                    )
                )
                if str(
                    item.get(
                        "evidence_digest",
                        "",
                    )
                )
            }
        )
    )

    registry = (
        orobouros_evolution_registry
        .register_pair(
            champion_receipt=
                champion_receipt,
            challenger_receipt=
                challenger_receipt,
            shadow_evaluation=
                shadow,
            evidence_refs=
                evidence_refs,
        )
    )

    gate = None
    mutation_request = None

    if notary_admission is not None:
        gate = (
            orobouros_promotion_gate
            .evaluate(
                registry_projection=
                    registry,
                shadow_evaluation=
                    shadow,
                notary_admission=
                    notary_admission,
            )
        )

        if gate.get(
            "eligible_for_coda_mutation",
            False,
        ):
            mutation_request = (
                orobouros_promotion_gate
                .mutation_request(
                    gate
                )
            )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            "orobouros",
        "shadow":
            shadow,
        "registry":
            registry,
        "promotion_gate":
            gate,
        "coda_mutation_request":
            mutation_request,
        "promotion_executed":
            False,
        "coda_execution_performed":
            False,
        "notary_verification_performed":
            False,
        "authority_effect":
            authority_effect,
    }


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,
        "owner":
            owner,
        "persona_id":
            "orobouros",
        "shadow_evaluation":
            True,
        "champion_challenger_registry":
            True,
        "notary_admission_binding":
            True,
        "coda_mutation_request":
            True,
        "coda_execution_performed":
            False,
        "promotion_executed":
            False,
        "authority_effect":
            authority_effect,
    }


def selftest() -> dict[str, Any]:
    champion = {
        "composition_digest":
            "champion",
        "active_traits":
            [
                "analytical_rigor",
            ],
    }

    challenger = {
        "composition_digest":
            "challenger",
        "active_traits":
            [
                "analytical_rigor",
                "planning",
            ],
    }

    def evidence(
        name: str,
    ) -> dict[str, Any]:
        return {
            "owner":
                "palaver",
            "authority_effect":
                "none",
            "evidence_digest":
                name,
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

    champion_evidence = tuple(
        evidence(
            f"champion-{index}"
        )
        for index in range(
            5
        )
    )

    challenger_evidence = tuple(
        evidence(
            f"challenger-{index}"
        )
        for index in range(
            5
        )
    )

    first = project(
        champion_receipt=
            champion,
        challenger_receipt=
            challenger,
        champion_evidence=
            champion_evidence,
        challenger_evidence=
            challenger_evidence,
        minimum_samples=
            5,
        required_margin=
            0.0,
    )

    shadow_digest = (
        first[
            "shadow"
        ][
            "shadow_digest"
        ]
    )

    admitted = project(
        champion_receipt=
            champion,
        challenger_receipt=
            challenger,
        champion_evidence=
            champion_evidence,
        challenger_evidence=
            challenger_evidence,
        minimum_samples=
            5,
        required_margin=
            0.0,
        notary_admission=
            {
                "owner":
                    "notary",
                "admitted":
                    True,
                "admission_ref":
                    "notary://test",
                "evidence_digest":
                    shadow_digest,
            },
    )

    request = admitted.get(
        "coda_mutation_request"
    )

    if not isinstance(
        request,
        dict,
    ):
        raise (
            orobouros_evolution_runtime_error(
                "eligible evolution did not "
                "produce Coda mutation request"
            )
        )

    if request.get(
        "executed"
    ):
        raise (
            orobouros_evolution_runtime_error(
                "Envoy executed Coda mutation"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "registry_digest":
            admitted[
                "registry"
            ][
                "registry_digest"
            ],
        "gate_digest":
            admitted[
                "promotion_gate"
            ][
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
