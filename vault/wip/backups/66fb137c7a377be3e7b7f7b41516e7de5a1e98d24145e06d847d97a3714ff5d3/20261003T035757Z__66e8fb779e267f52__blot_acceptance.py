#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.translucent.blot_verify import (
    VerificationReport,
)


name = "blot."
schema = "savant.translucent.blot.acceptance.v1"
authority_effect = "none"
mutation_effect = "none"
projection_only = True


class BlotAcceptanceError(ValueError):
    pass


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise BlotAcceptanceError(
            "value is not canonical-json compatible"
        ) from exc


def _digest(value: Any) -> str:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    elif isinstance(value, bytes):
        raw = value
    else:
        raw = _canonical(
            value
        ).encode("utf-8")

    return hashlib.sha256(
        raw
    ).hexdigest()


def _text(
    value: Any,
    field_name: str,
) -> str:
    result = str(
        value or ""
    ).strip()

    if not result:
        raise BlotAcceptanceError(
            f"{field_name} is required"
        )

    return result


@dataclass(frozen=True)
class AcceptanceDecision:
    verification_digest: str
    source_digest: str
    construction_digest: str
    execution_digest: str
    projection_digest: str
    accepted: bool
    failure_routes: tuple[
        tuple[str, str],
        ...
    ] = ()

    def normalized(
        self,
    ) -> dict[str, Any]:
        routes = [
            {
                "category":
                    _text(
                        category,
                        "category",
                    ),
                "causal_stage_id":
                    _text(
                        stage_id,
                        "causal_stage_id",
                    ),
            }
            for category, stage_id
            in self.failure_routes
        ]

        body = {
            "schema":
                schema,

            "name":
                name,

            "verification_digest":
                _text(
                    self.verification_digest,
                    "verification_digest",
                ),

            "source_digest":
                _text(
                    self.source_digest,
                    "source_digest",
                ),

            "construction_digest":
                _text(
                    self.construction_digest,
                    "construction_digest",
                ),

            "execution_digest":
                _text(
                    self.execution_digest,
                    "execution_digest",
                ),

            "projection_digest":
                _text(
                    self.projection_digest,
                    "projection_digest",
                ),

            "accepted":
                bool(
                    self.accepted
                ),

            "failure_routes":
                routes,

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,

            "creates_authority":
                False,
        }

        return {
            **body,
            "digest":
                _digest(
                    body
                ),
        }


def decide(
    report: VerificationReport
    | Mapping[str, Any],
) -> AcceptanceDecision:
    if isinstance(
        report,
        VerificationReport,
    ):
        normalized = (
            report.normalized()
        )
    elif isinstance(
        report,
        Mapping,
    ):
        normalized = dict(
            report
        )
    else:
        raise BlotAcceptanceError(
            "report must be a verification "
            "report or mapping"
        )

    report_schema = str(
        normalized.get(
            "schema",
            "",
        )
    ).strip()

    if (
        report_schema
        != "savant.translucent.blot.verification.v2"
    ):
        raise BlotAcceptanceError(
            "unsupported verification schema"
        )

    accepted = bool(
        normalized.get(
            "accepted",
            False,
        )
    )

    failures = normalized.get(
        "failures",
        ()
    )

    if not isinstance(
        failures,
        (
            list,
            tuple,
        ),
    ):
        raise BlotAcceptanceError(
            "verification failures must "
            "be a sequence"
        )

    routes: list[
        tuple[
            str,
            str,
        ]
    ] = []

    for failure in failures:
        if not isinstance(
            failure,
            Mapping,
        ):
            raise BlotAcceptanceError(
                "verification failure must "
                "be a mapping"
            )

        routes.append(
            (
                _text(
                    failure.get(
                        "category"
                    ),
                    "failure.category",
                ),
                _text(
                    failure.get(
                        "causal_stage_id"
                    ),
                    "failure.causal_stage_id",
                ),
            )
        )

    if accepted and routes:
        raise BlotAcceptanceError(
            "accepted verification cannot "
            "contain failure routes"
        )

    if (
        not accepted
        and not routes
    ):
        raise BlotAcceptanceError(
            "rejected verification must "
            "contain at least one failure route"
        )

    decision = AcceptanceDecision(
        verification_digest=
            _text(
                normalized.get(
                    "digest"
                )
                or _digest(
                    normalized
                ),
                "verification_digest",
            ),

        source_digest=
            _text(
                normalized.get(
                    "source_digest"
                ),
                "source_digest",
            ),

        construction_digest=
            _text(
                normalized.get(
                    "construction_digest"
                ),
                "construction_digest",
            ),

        execution_digest=
            _text(
                normalized.get(
                    "execution_digest"
                ),
                "execution_digest",
            ),

        projection_digest=
            _text(
                normalized.get(
                    "projection_digest"
                ),
                "projection_digest",
            ),

        accepted=
            accepted,

        failure_routes=
            tuple(
                routes
            ),
    )

    decision.normalized()

    return decision


def manifest() -> dict[str, Any]:
    body = {
        "schema":
            schema,

        "name":
            name,

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,

        "projection_only":
            projection_only,

        "input_schema":
            "savant.translucent.blot.verification.v2",

        "accepted_effect":
            (
                "projection-acceptance-only"
            ),

        "rejected_effect":
            (
                "causal-stage-routing-only"
            ),

        "creates_authority":
            False,

        "mutates_construction":
            False,

        "mutates_projection":
            False,
    }

    return {
        **body,
        "digest":
            _digest(
                body
            ),
    }


__all__ = [
    "AcceptanceDecision",
    "BlotAcceptanceError",
    "authority_effect",
    "decide",
    "manifest",
    "mutation_effect",
    "name",
    "projection_only",
    "schema",
]


if __name__ == "__main__":
    print(
        json.dumps(
            manifest(),
            indent=2,
            sort_keys=True,
        )
    )
