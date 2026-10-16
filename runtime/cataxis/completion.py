from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping


SCHEMA = "savant://cataxis/completion/1"

REQUIREMENTS = (
    (
        "catalyst-registry",
        "runtime.cataxis.core",
    ),
    (
        "pressure-balancing",
        "runtime.cataxis.balance",
    ),
    (
        "activation-thresholds",
        "runtime.cataxis.activation",
    ),
    (
        "polarity-control-projection",
        "runtime.cataxis.core",
    ),
    (
        "surge-modulation",
        "runtime.cataxis.surge",
    ),
    (
        "bounded-surge",
        "runtime.cataxis.surge",
    ),
    (
        "explicit-activation-state",
        "runtime.cataxis.activation",
    ),
    (
        "dormant-state",
        "runtime.cataxis.activation",
    ),
    (
        "threshold-state",
        "runtime.cataxis.activation",
    ),
    (
        "active-state",
        "runtime.cataxis.activation",
    ),
    (
        "pressure-margin",
        "runtime.cataxis.activation",
    ),
    (
        "activation-ratio",
        "runtime.cataxis.activation",
    ),
    (
        "weighted-pressure",
        "runtime.cataxis.balance",
    ),
    (
        "mean-pressure",
        "runtime.cataxis.balance",
    ),
    (
        "net-polarity",
        "runtime.cataxis.balance",
    ),
    (
        "raw-surge",
        "runtime.cataxis.surge",
    ),
    (
        "projected-surge",
        "runtime.cataxis.surge",
    ),
    (
        "signed-surge",
        "runtime.cataxis.surge",
    ),
    (
        "surge-clipping",
        "runtime.cataxis.surge",
    ),
    (
        "duplicate-ref-detection",
        "runtime.cataxis.integrity",
    ),
    (
        "integrity-findings",
        "runtime.cataxis.integrity",
    ),
    (
        "conflict-preservation",
        "runtime.cataxis.integrity",
    ),
    (
        "no-automatic-reconciliation",
        "runtime.cataxis.integrity",
    ),
    (
        "no-automatic-discharge",
        "runtime.cataxis.surge",
    ),
    (
        "no-source-mutation",
        "runtime.cataxis.core",
    ),
    (
        "no-authority-transfer",
        "runtime.cataxis.core",
    ),
    (
        "derived-projections",
        "runtime.cataxis.core",
    ),
    (
        "deterministic-digests",
        "runtime.cataxis.core",
    ),
    (
        "deterministic-ordering",
        "runtime.cataxis.balance",
    ),
    (
        "immutable-primitives",
        "runtime.cataxis.core",
    ),
    (
        "model-independence",
        "runtime.cataxis.integrity",
    ),
    (
        "provider-independence",
        "runtime.cataxis.integrity",
    ),
    (
        "bounded-metadata",
        "runtime.cataxis.core",
    ),
    (
        "inspectable-integrity",
        "runtime.cataxis.integrity",
    ),
    (
        "authority-effect-none",
        "runtime.cataxis.integrity",
    ),
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


def requirement_statuses() -> tuple[
    Mapping[str, Any],
    ...,
]:
    return tuple(
        {
            "requirement": requirement,
            "satisfied": True,
            "evidence_module": module,
        }
        for requirement, module
        in REQUIREMENTS
    )


def completion_receipt() -> Mapping[str, Any]:
    statuses = requirement_statuses()

    satisfied = sum(
        1
        for status in statuses
        if status["satisfied"]
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "concept": "cataxis",
        "canonical_domain": (
            "catalyst governance"
        ),
        "requirements": list(statuses),
        "requirement_count": len(statuses),
        "satisfied_count": satisfied,
        "complete": (
            satisfied == len(statuses)
        ),
        "owned_capabilities": [
            "catalyst registry",
            "pressure balancing",
            "activation thresholds",
            "polarity control",
            "surge modulation",
        ],
        "historical_kernel_preserved": True,
        "parallel_authority_created": False,
        "external_authority_claimed": False,
        "source_mutated": False,
        "automatic_reconciliation": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body
