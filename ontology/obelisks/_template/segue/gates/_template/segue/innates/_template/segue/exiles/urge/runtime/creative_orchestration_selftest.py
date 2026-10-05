from __future__ import annotations

import copy
import json
from typing import Any

from . import creative_orchestration as module


def _candidate(
    name: str,
    mechanism: str,
    *,
    difference: str,
) -> dict[str, str]:
    return {
        "name": name,
        "concept": (
            f"{name} converts a binding constraint "
            f"into the visible identity."
        ),
        "mechanism": mechanism,
        "rationale": (
            "The concept derives distinction from "
            "a structural rule rather than styling."
        ),
        "assumption_broken": (
            "identity requires a conventional symbol"
        ),
        "structural_difference": difference,
        "risk": (
            "the mechanism could become obscure "
            "without disciplined execution"
        ),
        "test": (
            "remove styling and verify that the "
            "mechanism remains distinguishable"
        ),
    }


def _fake_opus_text(
    *,
    message: str,
    system: str,
    context: dict[str, Any],
    required_capabilities=(),
    required_layers=(),
) -> dict[str, Any]:
    del system
    del context
    del required_capabilities
    del required_layers

    if "adversarial synthesis" in message.lower():
        candidates = [
            _candidate(
                "hinge",
                (
                    "one discontinuity changes role "
                    "across scale while preserving "
                    "the same silhouette"
                ),
                difference=(
                    "identity is produced by a "
                    "scale-dependent relationship"
                ),
            ),
            _candidate(
                "counterform",
                (
                    "the absent region carries the "
                    "primary semantic event"
                ),
                difference=(
                    "the mark is identified by what "
                    "is withheld rather than added"
                ),
            ),
            _candidate(
                "relay",
                (
                    "two incomplete primitives become "
                    "complete only through adjacency"
                ),
                difference=(
                    "identity emerges from relationship "
                    "rather than either primitive"
                ),
            ),
            _candidate(
                "phase",
                (
                    "one primitive occupies two "
                    "apparently incompatible readings "
                    "without changing geometry"
                ),
                difference=(
                    "semantic multiplicity emerges "
                    "from one stable construction"
                ),
            ),
            _candidate(
                "pressure",
                (
                    "a constraint visibly deforms a "
                    "primitive and the deformation "
                    "becomes the identifying feature"
                ),
                difference=(
                    "constraint is causal rather than "
                    "an obstacle"
                ),
            ),
            _candidate(
                "interval",
                (
                    "spacing itself carries the "
                    "identity while the solids remain "
                    "deliberately ordinary"
                ),
                difference=(
                    "the active primitive is relational "
                    "distance"
                ),
            ),
        ]
    else:
        candidates = [
            _candidate(
                "fold",
                (
                    "one primitive changes semantic "
                    "role at a single controlled fold"
                ),
                difference="meaning is carried by topology",
            ),
            _candidate(
                "threshold",
                (
                    "a boundary is interrupted exactly "
                    "where the identity changes state"
                ),
                difference="transition is the symbol",
            ),
            _candidate(
                "echo",
                (
                    "one structural event is repeated "
                    "at a different scale with changed "
                    "functional meaning"
                ),
                difference="recursion carries identity",
            ),
            _candidate(
                "void",
                (
                    "the dominant shape is never drawn "
                    "and exists only through surrounding "
                    "geometry"
                ),
                difference="absence is the canonical event",
            ),
            _candidate(
                "offset",
                (
                    "two aligned systems disagree at "
                    "one intentional coordinate"
                ),
                difference=(
                    "controlled disagreement produces recognition"
                ),
            ),
            _candidate(
                "splice",
                (
                    "two incompatible construction "
                    "rules share one exact primitive"
                ),
                difference=(
                    "one primitive resolves a semantic paradox"
                ),
            ),
        ]

    return {
        "text": json.dumps(
            {"candidates": candidates},
            sort_keys=True,
        ),
        "provider": "selftest",
        "model": "deterministic-fixture",
        "usage": {},
        "lineage": {
            "owner": "exile:opus",
            "executor": "selftest",
        },
    }


def _semantic_projection(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return {
            key: _semantic_projection(item)
            for key, item in value.items()
            if key not in {
                "run_id",
                "receipt_id",
                "created_ns",
                "recorded_ns",
                "timestamp_ns",
            }
        }

    if isinstance(value, list):
        return [
            _semantic_projection(item)
            for item in value
        ]

    return value


def main() -> int:
    original = module._opus_text

    try:
        module._opus_text = _fake_opus_text

        engine = module.creative_engine(
            module.creative_policy(
                divergence_passes=4,
                candidates_per_pass=6,
                frontier_size=7,
                synthesis_candidates=6,
            )
        )

        request = {
            "objective": (
                "create a distinctive identity "
                "whose mechanism survives removal "
                "of decorative styling"
            ),
            "constraints": (
                "must remain coherent",
                "must remain usable",
            ),
            "invariants": (
                "preserve semantic identity",
            ),
            "cliches": (
                "generic geometric icon",
                "arbitrary monogram",
                "generic gradient",
            ),
            "baselines": (
                "generic technology logo",
            ),
            "context": {
                "domain": "selftest",
            },
        }

        first = engine.project(**request)
        second = engine.project(**request)

    finally:
        module._opus_text = original

    first_semantic = _semantic_projection(
        copy.deepcopy(first)
    )

    second_semantic = _semantic_projection(
        copy.deepcopy(second)
    )

    first_semantic.pop("digest", None)
    second_semantic.pop("digest", None)

    assert first_semantic == second_semantic

    assert first["frontier"]
    assert first["first_generation"]
    assert first["synthesis"]

    assert (
        first["ownership"]["provider_orchestration"]
        == "exile:opus"
    )

    assert (
        first["ownership"]["structural_discrimination"]
        == "exile:underscore"
    )

    assert (
        first["ownership"]["iteration"]
        == "exile:urge"
    )

    assert (
        first["boundaries"]["creates_authority"]
        is False
    )

    assert (
        first["boundaries"]["exposes_hidden_chain_of_thought"]
        is False
    )

    first_vessel = first[
        "first_discrimination"
    ]

    second_vessel = second[
        "first_discrimination"
    ]

    assert (
        first_vessel["fingerprint"]
        == second_vessel["fingerprint"]
    )

    assert (
        first_vessel["run_id"]
        != second_vessel["run_id"]
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "semantic_replay": True,
                "vessel_fingerprint": (
                    first_vessel["fingerprint"]
                ),
                "distinct_receipts": True,
                "frontier_count": len(
                    first["frontier"]
                ),
            },
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
