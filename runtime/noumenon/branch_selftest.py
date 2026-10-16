import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.branch import (
    branch_heads,
    fork_points,
    project_branches,
)
from runtime.noumenon.state import (
    DevelopmentalConsequence,
    Experience,
    Significance,
    TransitionCandidate,
    empty_state,
)


def successor(
    predecessor,
    *,
    experience_id: str,
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
                "personal": 0.7,
            }
        ),
        consequences=(
            DevelopmentalConsequence(
                dimension="trust",
                delta=delta,
                causal_refs=(
                    experience_id,
                ),
            ),
        ),
    ).successor()


def main() -> int:
    root = empty_state(
        "branch-selftest"
    )

    first = successor(
        root,
        experience_id=(
            "experience:first"
        ),
        delta=0.1,
    )

    branch_a = successor(
        first,
        experience_id=(
            "experience:branch-a"
        ),
        delta=0.2,
    )

    branch_b = successor(
        first,
        experience_id=(
            "experience:branch-b"
        ),
        delta=-0.2,
    )

    branch_a_next = successor(
        branch_a,
        experience_id=(
            "experience:branch-a-next"
        ),
        delta=0.1,
    )

    states = (
        root,
        first,
        branch_a,
        branch_b,
        branch_a_next,
    )

    heads = branch_heads(
        states
    )

    assert {
        state.state_digest
        for state in heads
    } == {
        branch_b.state_digest,
        branch_a_next.state_digest,
    }

    forks = fork_points(
        states
    )

    assert forks == (
        first.state_digest,
    )

    projection = (
        project_branches(
            states
        ).projection()
    )

    assert (
        projection[
            "noumenon_id"
        ]
        == root.noumenon_id
    )

    assert (
        projection["ambiguous"]
        is True
    )

    assert (
        projection[
            "fork_points"
        ]
        == [
            first.state_digest
        ]
    )

    assert len(
        projection["heads"]
    ) == 2

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
