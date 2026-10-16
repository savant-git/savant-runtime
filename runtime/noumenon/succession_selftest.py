import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.state import (
    DevelopmentalConsequence,
    Experience,
    Significance,
    TransitionCandidate,
    empty_state,
)
from runtime.noumenon.succession import (
    ancestry_projection,
    classify_fork,
    succession_edge,
    validate_linear_continuity,
)


def successor(
    predecessor,
    *,
    experience_id: str,
    dimension: str,
    delta: float,
):
    return TransitionCandidate(
        predecessor=predecessor,
        experience=Experience(
            id=experience_id,
            observed=True,
            owned=True,
        ),
        significance=Significance(
            dimensions={
                "personal": 0.5,
            }
        ),
        consequences=(
            DevelopmentalConsequence(
                dimension=dimension,
                delta=delta,
                causal_refs=(
                    experience_id,
                ),
            ),
        ),
    ).successor()


def main() -> int:
    root = empty_state(
        "succession-selftest"
    )

    first = successor(
        root,
        experience_id="experience:first",
        dimension="trust",
        delta=0.2,
    )

    second = successor(
        first,
        experience_id="experience:second",
        dimension="curiosity",
        delta=0.3,
    )

    assert (
        root.noumenon_id
        == first.noumenon_id
        == second.noumenon_id
    )

    assert (
        first.predecessor_id
        == root.state_digest
    )

    assert (
        second.predecessor_id
        == first.state_digest
    )

    edge = succession_edge(
        root,
        first,
    )

    assert (
        edge.predecessor_state_digest
        == root.state_digest
    )

    assert (
        edge.successor_state_digest
        == first.state_digest
    )

    linear = validate_linear_continuity(
        (
            root,
            first,
            second,
        )
    )

    assert linear["continuous"]

    branch_a = successor(
        root,
        experience_id="experience:branch-a",
        dimension="trust",
        delta=0.4,
    )

    branch_b = successor(
        root,
        experience_id="experience:branch-b",
        dimension="trust",
        delta=-0.4,
    )

    assert (
        branch_a.state_digest
        != branch_b.state_digest
    )

    assert (
        branch_a.noumenon_id
        == branch_b.noumenon_id
        == root.noumenon_id
    )

    fork = classify_fork(
        root,
        (
            branch_a,
            branch_b,
        ),
    )

    assert (
        fork.classification
        == "branch"
    )

    assert (
        len(
            fork.successor_state_digests
        )
        == 2
    )

    assert (
        branch_a.state_digest
        in fork.successor_state_digests
    )

    assert (
        branch_b.state_digest
        in fork.successor_state_digests
    )

    ancestry = ancestry_projection(
        (
            root,
            branch_a,
            branch_b,
        )
    )

    assert (
        ancestry["roots"]
        == [root.state_digest]
    )

    assert len(
        ancestry["edges"]
    ) == 2

    assert (
        ancestry["authoritative"]
        is False
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
