from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from runtime.noumenon.state import (
    DevelopmentalConsequence,
    Experience,
    NoumenonState,
    Significance,
    TransitionCandidate,
)


@dataclass(frozen=True, slots=True)
class AppraisalInput:
    experience: Experience
    significance_dimensions: Mapping[str, float]
    uncertainty: Mapping[str, float]
    consequence_dimensions: Mapping[str, float]
    interpretation_refs: tuple[str, ...] = ()
    causal_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            self.consequence_dimensions
            and not self.causal_refs
        ):
            raise ValueError(
                "developmental consequences require causal_refs"
            )


def eligible_for_development(
    appraisal: AppraisalInput,
) -> bool:
    experience = appraisal.experience

    if not experience.observed:
        return False

    if not experience.owned:
        return False

    if not appraisal.significance_dimensions:
        return False

    return any(
        abs(float(value)) > 0.0
        for value
        in appraisal.significance_dimensions.values()
    )


def build_transition_candidate(
    state: NoumenonState,
    appraisal: AppraisalInput,
) -> TransitionCandidate | None:
    if not eligible_for_development(appraisal):
        return None

    significance = Significance(
        dimensions=dict(
            appraisal.significance_dimensions
        ),
        interpretation_refs=(
            appraisal.interpretation_refs
        ),
        uncertainty=dict(appraisal.uncertainty),
    )

    consequences = tuple(
        DevelopmentalConsequence(
            dimension=dimension,
            delta=float(delta),
            causal_refs=appraisal.causal_refs,
        )
        for dimension, delta
        in sorted(
            appraisal.consequence_dimensions.items()
        )
        if float(delta) != 0.0
    )

    return TransitionCandidate(
        predecessor=state,
        experience=appraisal.experience,
        significance=significance,
        consequences=consequences,
    )


def appraisal_from_projection(
    experience: Experience,
    projection: Mapping[str, object],
    *,
    causal_refs: Sequence[str],
) -> AppraisalInput:
    raw_significance = projection.get(
        "significance_dimensions",
        {},
    )
    raw_uncertainty = projection.get(
        "uncertainty",
        {},
    )
    raw_consequences = projection.get(
        "consequence_dimensions",
        {},
    )
    raw_interpretations = projection.get(
        "interpretation_refs",
        (),
    )

    if not isinstance(raw_significance, Mapping):
        raise TypeError(
            "significance_dimensions must be a mapping"
        )

    if not isinstance(raw_uncertainty, Mapping):
        raise TypeError(
            "uncertainty must be a mapping"
        )

    if not isinstance(raw_consequences, Mapping):
        raise TypeError(
            "consequence_dimensions must be a mapping"
        )

    if not isinstance(
        raw_interpretations,
        (list, tuple),
    ):
        raise TypeError(
            "interpretation_refs must be a sequence"
        )

    return AppraisalInput(
        experience=experience,
        significance_dimensions={
            str(key): float(value)
            for key, value
            in raw_significance.items()
        },
        uncertainty={
            str(key): float(value)
            for key, value
            in raw_uncertainty.items()
        },
        consequence_dimensions={
            str(key): float(value)
            for key, value
            in raw_consequences.items()
        },
        interpretation_refs=tuple(
            str(value)
            for value in raw_interpretations
        ),
        causal_refs=tuple(causal_refs),
    )
