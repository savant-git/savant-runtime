import math
import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.relational_trajectory import (
    establish_relationship,
    relationship_projection,
    relationship_velocity,
    transition_relationship,
)


def main() -> int:
    trajectory = establish_relationship(
        "self:alpha",
        "person:beta",
        dimensions={
            "familiarity": 0.5,
            "trust": 0.8,
            "affection": 0.7,
            "safety": 0.8,
        },
        causal_refs=(
            "history:shared",
        ),
        evidence_refs=(
            "evidence:history",
        ),
        shared_history_refs=(
            "episode:first-meeting",
        ),
    )

    reverse = establish_relationship(
        "person:beta",
        "self:alpha",
        dimensions={
            "familiarity": 0.5,
            "trust": 0.2,
        },
    )

    assert (
        trajectory.current.dimensions[
            "trust"
        ]
        != reverse.current.dimensions[
            "trust"
        ]
    )

    ruptured, rupture = (
        transition_relationship(
            trajectory,
            deltas={
                "trust": -0.6,
                "safety": -0.5,
                "grievance": 0.8,
                "unresolvedness": 0.7,
            },
            causal_refs=(
                "experience:rupture",
            ),
            evidence_refs=(
                "evidence:rupture",
            ),
            shared_history_refs=(
                "episode:rupture",
            ),
        )
    )

    assert (
        ruptured.current.sequence
        == 1
    )

    assert (
        ruptured.current
        .predecessor_ref
        == trajectory.current.id
    )

    assert math.isclose(
        ruptured.current.dimensions[
            "trust"
        ],
        0.2,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    repaired, repair = (
        transition_relationship(
            ruptured,
            deltas={
                "trust": 0.2,
                "safety": 0.3,
                "grievance": -0.4,
                "unresolvedness": -0.5,
            },
            causal_refs=(
                "experience:repair",
            ),
            evidence_refs=(
                "evidence:repair",
            ),
            repair_refs=(
                "repair:alpha",
            ),
            shared_history_refs=(
                "episode:repair",
            ),
        )
    )

    assert (
        repaired.current.sequence
        == 2
    )

    assert (
        repaired.current
        .predecessor_ref
        == ruptured.current.id
    )

    assert (
        repaired.current.dimensions[
            "trust"
        ]
        < trajectory.current.dimensions[
            "trust"
        ]
    )

    assert (
        "evidence:rupture"
        in repaired.current
        .evidence_refs
    )

    assert (
        "repair:alpha"
        in repaired.current
        .repair_refs
    )

    velocity = relationship_velocity(
        repaired
    )

    assert math.isclose(
        velocity["trust"],
        0.2,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    projection = (
        relationship_projection(
            repaired
        )
    )

    assert (
        projection[
            "directional"
        ]
        is True
    )

    assert (
        projection[
            "forgiveness_erases_evidence"
        ]
        is False
    )

    assert (
        projection[
            "repair_restores_trust_automatically"
        ]
        is False
    )

    assert (
        projection[
            "reciprocity_implied"
        ]
        is False
    )

    assert (
        projection[
            "authoritative"
        ]
        is False
    )

    assert (
        rupture.successor_ref
        == ruptured.current.id
    )

    assert (
        repair.successor_ref
        == repaired.current.id
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
