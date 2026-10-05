import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.bandwidth import (
    BandwidthPolicy,
    apply_bandwidth,
    candidate_pressure,
)
from runtime.noumenon.state import (
    DevelopmentalConsequence,
    Experience,
    Significance,
    TransitionCandidate,
    empty_state,
)


def main() -> int:
    root = empty_state(
        "bandwidth-selftest"
    )

    candidate = TransitionCandidate(
        predecessor=root,
        experience=Experience(
            id="experience:bandwidth",
            observed=True,
            owned=True,
        ),
        significance=Significance(
            dimensions={
                "personal": 0.9,
            }
        ),
        consequences=(
            DevelopmentalConsequence(
                dimension="trust",
                delta=0.7,
                causal_refs=(
                    "experience:bandwidth",
                ),
            ),
            DevelopmentalConsequence(
                dimension="curiosity",
                delta=0.5,
                causal_refs=(
                    "experience:bandwidth",
                ),
            ),
            DevelopmentalConsequence(
                dimension="confidence",
                delta=0.4,
                causal_refs=(
                    "experience:bandwidth",
                ),
            ),
            DevelopmentalConsequence(
                dimension="attachment",
                delta=0.9,
                causal_refs=(
                    "experience:bandwidth",
                ),
            ),
        ),
    )

    assert (
        candidate_pressure(candidate)
        == 2.5
    )

    policy = BandwidthPolicy(
        maximum_consequences=2,
        maximum_absolute_delta=0.8,
        maximum_total_pressure=1.2,
    )

    bounded, decision = (
        apply_bandwidth(
            candidate,
            policy,
        )
    )

    assert decision.admitted

    assert (
        decision.reason
        == "bounded"
    )

    assert (
        decision.original_count
        == 4
    )

    assert (
        decision.retained_count
        == 2
    )

    assert (
        decision.retained_pressure
        <= 1.2
    )

    assert {
        consequence.dimension
        for consequence
        in bounded.consequences
    } == {
        "curiosity",
        "trust",
    }

    assert all(
        abs(consequence.delta)
        <= 0.8
        for consequence
        in bounded.consequences
    )

    successor = (
        bounded.successor()
    )

    assert (
        successor.noumenon_id
        == root.noumenon_id
    )

    assert (
        successor.predecessor_id
        == root.state_digest
    )

    assert (
        successor.generation
        == 1
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
