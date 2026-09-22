import math
import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.memory_dynamics import (
    ForgettingPolicy,
    MemoryTrace,
    forget,
    reconstruct,
    reconsolidate,
    residual_causality,
)


def main() -> int:
    trace = MemoryTrace(
        memory_ref="memory:event-a",
        retention=1.0,
        significance=0.8,
        accessibility=1.0,
        residual_effect=0.9,
        causal_refs=(
            "experience:event-a",
        ),
        evidence_refs=(
            "evidence:event-a",
        ),
    )

    policy = ForgettingPolicy(
        decay=0.5,
        significance_protection=0.75,
        residual_decay=0.1,
    )

    faded = forget(
        trace,
        policy=policy,
    )

    assert (
        faded.retention
        < trace.retention
    )

    assert (
        faded.retention
        > 0.5
    )

    assert (
        faded.residual_effect
        < trace.residual_effect
    )

    assert (
        faded.residual_effect
        > 0.0
    )

    assert trace.id in (
        faded.causal_refs
    )

    reconstruction = reconstruct(
        faded,
        causal_refs=(
            "recall:attempt-a",
        ),
    )

    assert (
        reconstruction.confidence
        < 1.0
    )

    assert (
        reconstruction.uncertainty
        > 0.0
    )

    reconsolidated = reconsolidate(
        faded,
        reconstruction,
        significance=0.9,
    )

    assert math.isclose(
        reconsolidated.significance,
        0.9,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    assert (
        reconsolidated
        .reconstruction_uncertainty
        >= faded
        .reconstruction_uncertainty
    )

    inaccessible = MemoryTrace(
        memory_ref="memory:forgotten",
        retention=0.0,
        significance=0.9,
        accessibility=0.0,
        residual_effect=0.7,
        causal_refs=(
            "experience:forgotten",
        ),
    )

    residual = residual_causality(
        inaccessible
    )

    assert (
        residual["accessible"]
        is False
    )

    assert (
        residual["causally_active"]
        is True
    )

    assert (
        residual[
            "memory_accuracy_inferred"
        ]
        is False
    )

    assert (
        residual[
            "interpretation_inferred"
        ]
        is False
    )

    assert (
        reconstruction.projection()[
            "authoritative"
        ]
        is False
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
