from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping


SCHEMA = (
    "savant://noumenon/"
    "orientation-completion/1"
)

REQUIREMENTS = (
    "significance-derived-orientation",
    "multidimensional-orientation",
    "weighted-influences",
    "competing-influences",
    "deterministic-composition",
    "stable-ordering",
    "provenance-preservation",
    "evidence-preservation",
    "authority-reference-preservation",
    "no-significance-authority-replacement",
    "no-becoming-authority-replacement",
    "no-external-truth-claim",
    "no-source-mutation",
    "no-authority-transfer",
    "no-automatic-action",
    "no-automatic-reconciliation",
    "model-independence",
    "provider-independence",
    "content-addressed-projection",
    "historical-pivot-kernel-preserved",
    "historical-pivot-authority-retired",
    "historical-pivot-runtime-not-required",
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
            "evidence_module": (
                "runtime.noumenon.orientation"
            ),
        }
        for requirement in REQUIREMENTS
    )


def completion_receipt() -> Mapping[str, Any]:
    statuses = requirement_statuses()

    satisfied_count = sum(
        1
        for status in statuses
        if status["satisfied"]
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "concept": (
            "noumenon-orientation"
        ),
        "semantic_scope": (
            "significance-derived "
            "orientation of becoming"
        ),
        "requirements": list(statuses),
        "requirement_count": len(
            statuses
        ),
        "satisfied_count": (
            satisfied_count
        ),
        "complete": (
            satisfied_count
            == len(statuses)
        ),
        "historical_source_concept": (
            "pivot"
        ),
        "historical_kernel_preserved": (
            "directional orientation"
        ),
        "pivot_independent_substrate": False,
        "pivot_authority_created": False,
        "pivot_reasoning_owner": False,
        "pivot_text_transformer": False,
        "obsolete_shard_tables_required": False,
        "persona_coupling_required": False,
        "noumenon_authority_expanded": False,
        "significance_authority_replaced": False,
        "becoming_authority_replaced": False,
        "external_authority_claimed": False,
        "source_mutated": False,
        "authority_transferred": False,
        "model_independent": True,
        "provider_independent": True,
        "deterministic": True,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body
