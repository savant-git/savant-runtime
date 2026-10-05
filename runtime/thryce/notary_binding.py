#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


OWNER = "living:thryce"
OPERATIONAL_OWNER = "exile:notary"

SCHEMA = "savant://runtime/thryce/notary-binding/1.0.0"


class ThryceNotaryBindingError(RuntimeError):
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


def normalize_identifier(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def normalize_sequence(
    value: Any,
) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        item = normalize_identifier(value)
        return (item,) if item else ()

    if isinstance(value, Mapping):
        source = value.keys()
    else:
        try:
            source = iter(value)
        except TypeError:
            source = (value,)

    normalized = {
        item
        for item in (
            normalize_identifier(value)
            for value in source
        )
        if item
    }

    return tuple(sorted(normalized))


@dataclass(
    frozen=True,
    slots=True,
)
class AssuranceRequest:
    subject: str
    validation_layers: tuple[str, ...]
    payload: Any
    provenance: Any = None
    lineage: Any = None
    dependencies: tuple[str, ...] = ()
    requested_by: str | None = None

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "subject": self.subject,
            "validation_layers": list(
                self.validation_layers
            ),
            "payload": self.payload,
            "provenance": self.provenance,
            "lineage": self.lineage,
            "dependencies": list(
                self.dependencies
            ),
            "requested_by": self.requested_by,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class AssuranceResult:
    subject: str
    passed: bool
    checks: tuple[
        Mapping[str, Any],
        ...
    ]
    request_digest: str
    authoritative: bool = False
    evidence_admitted: bool = False
    attested: bool = False

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/"
                "thryce/assurance-result/1.0.0"
            ),
            "owner": OWNER,
            "operational_owner": (
                OPERATIONAL_OWNER
            ),
            "subject": self.subject,
            "passed": self.passed,
            "checks": [
                dict(check)
                for check in self.checks
            ],
            "request_digest": (
                self.request_digest
            ),
            "authoritative": (
                self.authoritative
            ),
            "evidence_admitted": (
                self.evidence_admitted
            ),
            "attested": self.attested,
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


class ThryceNotaryBinding:
    """
    Reusable assurance mechanics for Notary-owned verification.

    Thryce may evaluate validation and health mechanics.
    It may not admit evidence, attest facts, or create authority.
    """

    VALIDATION_LAYERS = (
        "syntax",
        "type",
        "schema",
        "policy",
        "property",
        "graph",
        "integration",
        "replay",
        "regression",
    )

    def __init__(
        self,
        *,
        validators: Mapping[
            str,
            Callable[[Any], Any],
        ]
        | None = None,
    ) -> None:
        supplied = dict(
            validators or {}
        )

        unknown = (
            set(supplied)
            - set(
                self.VALIDATION_LAYERS
            )
        )

        if unknown:
            raise ThryceNotaryBindingError(
                "unknown validation layer(s): "
                + ", ".join(
                    sorted(unknown)
                )
            )

        self._validators = supplied

    def request(
        self,
        *,
        subject: str,
        payload: Any,
        validation_layers: Sequence[
            str
        ]
        | None = None,
        provenance: Any = None,
        lineage: Any = None,
        dependencies: Any = (),
        requested_by: str | None = None,
    ) -> AssuranceRequest:
        identity = normalize_identifier(
            subject
        )

        if not identity:
            raise ThryceNotaryBindingError(
                "subject is required"
            )

        layers = (
            tuple(
                self.VALIDATION_LAYERS
            )
            if validation_layers is None
            else normalize_sequence(
                validation_layers
            )
        )

        invalid = (
            set(layers)
            - set(
                self.VALIDATION_LAYERS
            )
        )

        if invalid:
            raise ThryceNotaryBindingError(
                "unknown validation layer(s): "
                + ", ".join(
                    sorted(invalid)
                )
            )

        return AssuranceRequest(
            subject=identity,
            validation_layers=layers,
            payload=payload,
            provenance=provenance,
            lineage=lineage,
            dependencies=normalize_sequence(
                dependencies
            ),
            requested_by=(
                normalize_identifier(
                    requested_by
                )
            ),
        )

    def assure(
        self,
        request: AssuranceRequest,
    ) -> AssuranceResult:
        request_projection = (
            request.projection()
        )

        checks: list[
            Mapping[str, Any]
        ] = []

        for layer in (
            request.validation_layers
        ):
            validator = (
                self._validators.get(
                    layer
                )
            )

            if validator is None:
                checks.append(
                    {
                        "layer": layer,
                        "executed": False,
                        "passed": True,
                        "reason": (
                            "no validator bound"
                        ),
                    }
                )

                continue

            try:
                result = validator(
                    request.payload
                )

                if isinstance(
                    result,
                    Mapping,
                ):
                    passed = bool(
                        result.get(
                            "passed",
                            result.get(
                                "valid",
                                result.get(
                                    "healthy",
                                    True,
                                ),
                            ),
                        )
                    )

                    details = dict(
                        result
                    )
                else:
                    passed = bool(
                        result
                    )

                    details = {
                        "result": result,
                    }

                checks.append(
                    {
                        "layer": layer,
                        "executed": True,
                        "passed": passed,
                        "details": details,
                    }
                )

            except Exception as exc:
                checks.append(
                    {
                        "layer": layer,
                        "executed": True,
                        "passed": False,
                        "error": str(exc),
                        "error_type": (
                            type(exc).__name__
                        ),
                    }
                )

        passed = all(
            bool(
                check.get(
                    "passed",
                    False,
                )
            )
            for check in checks
        )

        return AssuranceResult(
            subject=request.subject,
            passed=passed,
            checks=tuple(checks),
            request_digest=(
                request_projection[
                    "digest"
                ]
            ),
            authoritative=False,
            evidence_admitted=False,
            attested=False,
        )

    def status(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "operational_owner": (
                OPERATIONAL_OWNER
            ),
            "governing_verb": (
                "assures"
            ),
            "validation_layers": list(
                self.VALIDATION_LAYERS
            ),
            "bound_validators": sorted(
                self._validators
            ),
            "bound_validator_count": len(
                self._validators
            ),
            "thryce_may_validate": True,
            "thryce_may_assure": True,
            "thryce_may_project_health": True,
            "thryce_may_emit_receipts": True,
            "thryce_may_admit_evidence": False,
            "thryce_may_attest": False,
            "thryce_may_create_authority": False,
            "notary_owns_verification": True,
            "notary_owns_evidence_admission": True,
            "notary_owns_attestation": True,
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def bind_notary(
    *,
    validators: Mapping[
        str,
        Callable[[Any], Any],
    ]
    | None = None,
) -> ThryceNotaryBinding:
    return ThryceNotaryBinding(
        validators=validators
    )


def main() -> int:
    binding = bind_notary(
        validators={
            "syntax": (
                lambda payload: {
                    "passed": (
                        payload is not None
                    )
                }
            ),
        }
    )

    request = binding.request(
        subject=(
            "integration:test:"
            "thryce:notary"
        ),
        payload={
            "example": True,
        },
        validation_layers=(
            "syntax",
        ),
        provenance={
            "source": (
                "focused-self-check"
            ),
        },
        requested_by=(
            "exile:notary"
        ),
    )

    result = binding.assure(
        request
    )

    output = {
        "status": binding.status(),
        "assurance": (
            result.projection()
        ),
    }

    print(
        json.dumps(
            output,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if result.passed
        and result.evidence_admitted
        is False
        and result.attested is False
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
