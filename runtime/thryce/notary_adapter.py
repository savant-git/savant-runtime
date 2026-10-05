#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .notary_binding import (
    AssuranceRequest,
    AssuranceResult,
    ThryceNotaryBinding,
    ThryceNotaryBindingError,
    bind_notary,
)


OWNER = "living:thryce"
NOTARY_OWNER = "exile:notary"
SCHEMA = "savant://runtime/thryce/notary-adapter/1.0.0"


class NotaryAdapterError(RuntimeError):
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
class NotaryAssurancePacket:
    request: AssuranceRequest
    result: AssuranceResult

    def projection(self) -> dict[str, Any]:
        request = self.request.projection()
        result = self.result.projection()

        payload = {
            "schema": (
                "savant://runtime/thryce/"
                "notary-assurance-packet/1.0.0"
            ),
            "owner": OWNER,
            "verification_owner": NOTARY_OWNER,
            "request": request,
            "assurance": result,
            "passed": result["passed"],
            "authoritative": False,
            "evidence_admitted": False,
            "attested": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(payload)

        return payload


class NotaryAssuranceAdapter:
    """
    Provides Thryce assurance mechanics to Notary without
    transferring Notary authority into Thryce.
    """

    def __init__(
        self,
        *,
        validators: Mapping[
            str,
            Callable[[Any], Any],
        ]
        | None = None,
        binding: ThryceNotaryBinding | None = None,
    ) -> None:
        if (
            validators is not None
            and binding is not None
        ):
            raise NotaryAdapterError(
                "supply validators or binding, not both"
            )

        self.binding = (
            binding
            if binding is not None
            else bind_notary(
                validators=validators
            )
        )

    def assure(
        self,
        *,
        subject: str,
        payload: Any,
        validation_layers: Sequence[str] | None = None,
        provenance: Any = None,
        lineage: Any = None,
        dependencies: Any = (),
    ) -> NotaryAssurancePacket:
        try:
            request = self.binding.request(
                subject=subject,
                payload=payload,
                validation_layers=validation_layers,
                provenance=provenance,
                lineage=lineage,
                dependencies=dependencies,
                requested_by=NOTARY_OWNER,
            )

            result = self.binding.assure(
                request
            )

        except ThryceNotaryBindingError as exc:
            raise NotaryAdapterError(
                str(exc)
            ) from exc

        return NotaryAssurancePacket(
            request=request,
            result=result,
        )

    def status(self) -> dict[str, Any]:
        binding_status = (
            self.binding.status()
        )

        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "verification_owner": NOTARY_OWNER,
            "binding": binding_status,
            "delegation": {
                "validation_mechanics": (
                    "thryce"
                ),
                "verification_decision": (
                    "notary"
                ),
                "evidence_admission": (
                    "notary"
                ),
                "attestation": (
                    "notary"
                ),
            },
            "thryce_authority_effect": "none",
            "thryce_can_admit_evidence": False,
            "thryce_can_attest": False,
            "thryce_can_manufacture_authority": False,
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def adapter(
    *,
    validators: Mapping[
        str,
        Callable[[Any], Any],
    ]
    | None = None,
) -> NotaryAssuranceAdapter:
    return NotaryAssuranceAdapter(
        validators=validators
    )


def main() -> int:
    instance = adapter(
        validators={
            "syntax": (
                lambda value: {
                    "passed": (
                        value is not None
                    )
                }
            ),
        }
    )

    packet = instance.assure(
        subject=(
            "integration:test:"
            "notary-assurance"
        ),
        payload={
            "valid": True,
        },
        validation_layers=(
            "syntax",
        ),
        provenance={
            "source": (
                "focused-integration-test"
            ),
        },
    )

    result = {
        "status": instance.status(),
        "packet": packet.projection(),
    }

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if (
            packet.result.passed
            and packet.result.attested
            is False
            and packet.result.evidence_admitted
            is False
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
