from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from runtime.cataxis.activation import (
    activation_state,
)
from runtime.cataxis.core import Catalyst
from runtime.cataxis.surge import (
    surge_state,
)


SCHEMA = "savant://cataxis/integrity/1"

SEVERITIES = (
    "info",
    "warning",
    "conflict",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class IntegrityFinding:
    code: str
    severity: str
    catalyst_refs: tuple[str, ...]
    detail: str

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError(
                "finding code is required"
            )

        if self.severity not in SEVERITIES:
            raise ValueError(
                "unsupported finding severity"
            )

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "code": self.code,
            "severity": self.severity,
            "catalyst_refs": list(
                self.catalyst_refs
            ),
            "detail": self.detail,
            "finding_is_observation": True,
            "source_mutated": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


def inspect_integrity(
    catalysts: Sequence[Catalyst],
) -> tuple[IntegrityFinding, ...]:
    ordered = tuple(
        sorted(
            catalysts,
            key=lambda item: (
                item.catalyst_ref,
                item.id,
            ),
        )
    )

    findings: list[
        IntegrityFinding
    ] = []

    by_ref: dict[
        str,
        list[Catalyst],
    ] = {}

    for catalyst in ordered:
        by_ref.setdefault(
            catalyst.catalyst_ref,
            [],
        ).append(catalyst)

    for ref, instances in sorted(
        by_ref.items()
    ):
        if len(instances) > 1:
            findings.append(
                IntegrityFinding(
                    code=(
                        "duplicate-catalyst-ref"
                    ),
                    severity="conflict",
                    catalyst_refs=tuple(
                        item.id
                        for item in instances
                    ),
                    detail=(
                        "multiple catalyst "
                        "instances share one "
                        "semantic reference"
                    ),
                )
            )

    for catalyst in ordered:
        activation = activation_state(
            catalyst
        )

        surge = surge_state(
            catalyst,
            activation,
        )

        if (
            activation.state == "active"
            and catalyst.surge_limit == 0.0
        ):
            findings.append(
                IntegrityFinding(
                    code="active-zero-surge-limit",
                    severity="warning",
                    catalyst_refs=(
                        catalyst.id,
                    ),
                    detail=(
                        "active catalyst has "
                        "a zero surge limit"
                    ),
                )
            )

        if surge.clipped:
            findings.append(
                IntegrityFinding(
                    code="surge-clipped",
                    severity="info",
                    catalyst_refs=(
                        catalyst.id,
                    ),
                    detail=(
                        "raw surge exceeds "
                        "configured surge limit"
                    ),
                )
            )

        if (
            catalyst.threshold == 0.0
            and catalyst.pressure > 0.0
        ):
            findings.append(
                IntegrityFinding(
                    code="zero-threshold-active",
                    severity="info",
                    catalyst_refs=(
                        catalyst.id,
                    ),
                    detail=(
                        "positive pressure is "
                        "active against a zero "
                        "threshold"
                    ),
                )
            )

    return tuple(
        sorted(
            findings,
            key=lambda item: (
                item.severity,
                item.code,
                item.catalyst_refs,
            ),
        )
    )


def integrity_receipt(
    catalysts: Sequence[Catalyst],
) -> Mapping[str, Any]:
    findings = inspect_integrity(
        catalysts
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "findings": [
            finding.projection()
            for finding in findings
        ],
        "finding_count": len(
            findings
        ),
        "conflict_count": sum(
            1
            for finding in findings
            if finding.severity
            == "conflict"
        ),
        "warning_count": sum(
            1
            for finding in findings
            if finding.severity
            == "warning"
        ),
        "info_count": sum(
            1
            for finding in findings
            if finding.severity
            == "info"
        ),
        "conflicts_preserved": True,
        "automatic_reconciliation": False,
        "automatic_mutation": False,
        "source_mutated": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body
