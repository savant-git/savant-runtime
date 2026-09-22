import math
import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.salience import (
    SalienceSignal,
    SalienceWeights,
    compete,
    salience_projection,
    score_salience,
)


def main() -> int:
    weights = SalienceWeights()

    ordinary = SalienceSignal(
        subject_ref="experience:ordinary",
        significance=0.2,
        surprise=0.1,
        curiosity=0.1,
        commitment=0.0,
        residue=0.0,
        relational=0.1,
        unresolved=0.0,
    )

    rupture = SalienceSignal(
        subject_ref="experience:rupture",
        significance=0.9,
        surprise=0.8,
        curiosity=0.6,
        commitment=0.7,
        residue=0.9,
        relational=1.0,
        unresolved=0.8,
    )

    question = SalienceSignal(
        subject_ref="question:unresolved",
        significance=0.5,
        surprise=0.3,
        curiosity=1.0,
        commitment=0.2,
        residue=0.1,
        relational=0.0,
        unresolved=1.0,
    )

    ordinary_score = score_salience(
        ordinary,
        weights,
    )

    rupture_score = score_salience(
        rupture,
        weights,
    )

    question_score = score_salience(
        question,
        weights,
    )

    assert (
        rupture_score.score
        > question_score.score
        > ordinary_score.score
    )

    expected = (
        0.9
        + 0.8
        + 0.6
        + 0.7
        + 0.9
        + 1.0
        + 0.8
    ) / 7.0

    assert math.isclose(
        rupture_score.score,
        expected,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    selected = compete(
        (
            ordinary,
            rupture,
            question,
        ),
        weights=weights,
        capacity=2,
    )

    assert (
        selected[0].id
        == rupture.id
    )

    assert (
        selected[1].id
        == question.id
    )

    projection = (
        salience_projection(
            (
                ordinary,
                rupture,
                question,
            ),
            weights=weights,
            capacity=2,
        )
    )

    assert (
        projection[
            "selected_refs"
        ]
        == [
            rupture.id,
            question.id,
        ]
    )

    assert (
        projection[
            "authoritative"
        ]
        is False
    )

    assert (
        rupture.projection()[
            "authority_effect"
        ]
        == "none"
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
