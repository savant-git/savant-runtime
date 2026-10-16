#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from runtime.thryce import (
    NotaryAssuranceAdapter,
    NotaryAssurancePacket,
    notary_adapter,
)


OWNER = "exile:notary"
MECHANICS_OWNER = "living:thryce"

SCHEMA = "savant://runtime/notary/thryce-assurance/1.0.0"


class NotaryThryceAssuranceError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class VerificationCandidate:
    subject: str
    payload: Any
    provenance: Any = None
    lineage: Any = None
    dependencies: tuple[str, ...] = ()

    def projection(self) -> dict[str, Any]:
        payload = {
            "subject": self.subject,
            "payload": self.payload,
            "provenance": self.provenance,
            "lineage": self.lineage,
            "dependencies": list(
                self.dependencies
            ),
        }

        payload["digest"] = digest(
            payload
        )

        return payload


class NotaryThryceAssurance:
    """
    Notary-owned entrypoint to Thryce assurance mechanics.

    This layer intentionally stops before evidence admission,
    verification judgment, or attestation. Those remain Notary
    operations and are not manufactured by Thryce.
    """

    def __init__(
        self,
        *,
        validators: Mapping[
            str,
            Callable[[Any], Any],
        ]
        | None = None,
        adapter: NotaryAssuranceAdapter | None = None,
    ) -> None:
        if (
            validators is not None
            and adapter is not None
        ):
            raise NotaryThryceAssuranceError(
                "supply validators or adapter, not both"
            )

        self._adapter = (
            adapter
            if adapter is not None
            else notary_adapter(
                validators=validators
            )
        )

    def candidate(
        self,
        *,
        subject: str,
        payload: Any,
        provenance: Any = None,
        lineage: Any = None,
        dependencies: Sequence[str] = (),
    ) -> VerificationCandidate:
        identity = str(
            subject or ""
        ).strip()

        if not identity:
            raise NotaryThryceAssuranceError(
                "subject is required"
            )

        return VerificationCandidate(
            subject=identity,
            payload=payload,
            provenance=provenance,
            lineage=lineage,
            dependencies=tuple(
                sorted(
                    {
                        str(item).strip()
                        for item in dependencies
                        if str(item).strip()
                    }
                )
            ),
        )

    def assure(
        self,
        candidate: VerificationCandidate,
        *,
        validation_layers: Sequence[str] | None = None,
    ) -> NotaryAssurancePacket:
        return self._adapter.assure(
            subject=candidate.subject,
            payload=candidate.payload,
            validation_layers=validation_layers,
            provenance=candidate.provenance,
            lineage=candidate.lineage,
            dependencies=candidate.dependencies,
        )

    def projection(
        self,
        candidate: VerificationCandidate,
        *,
        validation_layers: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        packet = self.assure(
            candidate,
            validation_layers=validation_layers,
        )

        assurance = packet.projection()

        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "mechanics_owner": MECHANICS_OWNER,
            "candidate": candidate.projection(),
            "assurance": assurance,
            "assurance_passed": (
                packet.result.passed
            ),
            "verification_decision": None,
            "evidence_admitted": False,
            "attested": False,
            "authority_created": False,
            "authority_mutated": False,
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload

    def status(self) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/notary/"
                "thryce-assurance-status/1.0.0"
            ),
            "owner": OWNER,
            "mechanics_owner": MECHANICS_OWNER,
            "assurance_mechanics_bound": True,
            "verification_owner": OWNER,
            "evidence_admission_owner": OWNER,
            "attestation_owner": OWNER,
            "thryce_can_verify": False,
            "thryce_can_admit_evidence": False,
            "thryce_can_attest": False,
            "thryce_can_create_authority": False,
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def assurance(
    *,
    validators: Mapping[
        str,
        Callable[[Any], Any],
    ]
    | None = None,
) -> NotaryThryceAssurance:
    return NotaryThryceAssurance(
        validators=validators
    )


def main() -> int:
    instance = assurance(
        validators={
            "syntax": (
                lambda value: {
                    "passed": (
                        value is not None
                    ),
                }
            ),
        }
    )

    candidate = instance.candidate(
        subject=(
            "integration:test:"
            "notary:thryce"
        ),
        payload={
            "valid": True,
        },
        provenance={
            "source": (
                "focused-integration-test"
            ),
        },
    )

    result = instance.projection(
        candidate,
        validation_layers=(
            "syntax",
        ),
    )

    print(
        json.dumps(
            {
                "status": instance.status(),
                "result": result,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if (
            result[
                "assurance_passed"
            ]
            and result[
                "verification_decision"
            ]
            is None
            and result[
                "evidence_admitted"
            ]
            is False
            and result[
                "attested"
            ]
            is False
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
