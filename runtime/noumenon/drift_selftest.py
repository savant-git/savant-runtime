import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.drift import (
    DriftEvidence,
    diagnose_drift,
    drift_projection,
)


def main() -> int:
    growth = DriftEvidence(
        source_ref="transition:growth",
        continuity=1.0,
        causal_support=0.95,
        authority_support=0.9,
        unexplained_change=0.05,
        state_integrity=1.0,
        provider_dependence=0.0,
        contradiction=0.1,
        evidence_refs=(
            "evidence:growth",
        ),
    )

    diagnosis = diagnose_drift(
        (growth,)
    )

    assert (
        diagnosis.drift_class
        == "growth"
    )

    assert diagnosis.confidence > 0.0

    contaminated = DriftEvidence(
        source_ref=(
            "transition:provider-shift"
        ),
        continuity=0.5,
        causal_support=0.05,
        authority_support=0.1,
        unexplained_change=1.0,
        state_integrity=0.9,
        provider_dependence=1.0,
        contradiction=0.2,
        evidence_refs=(
            "evidence:provider-shift",
        ),
    )

    diagnosis = diagnose_drift(
        (contaminated,)
    )

    assert (
        diagnosis.drift_class
        == "provider_contamination"
    )

    assert (
        diagnosis.auto_revert
        is False
    )

    lost = DriftEvidence(
        source_ref="transition:loss",
        continuity=0.0,
        causal_support=0.0,
        authority_support=0.5,
        unexplained_change=0.2,
        state_integrity=0.0,
        provider_dependence=0.0,
        contradiction=0.0,
    )

    diagnosis = diagnose_drift(
        (lost,)
    )

    assert (
        diagnosis.drift_class
        == "state_loss"
    )

    projection = drift_projection(
        (
            growth,
            contaminated,
        )
    )

    assert (
        projection[
            "automatic_reversion"
        ]
        is False
    )

    assert (
        projection[
            "contradictions_preserved"
        ]
        is True
    )

    assert (
        projection[
            "diagnosis_is_authority"
        ]
        is False
    )

    assert (
        projection[
            "authoritative"
        ]
        is False
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
