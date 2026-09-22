import math
import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.conscience import (
    ConscienceAppraisal,
    Repair,
    apply_repair,
    conscience_projection,
    derive_moral_residue,
)


def main() -> int:
    appraisal = ConscienceAppraisal(
        action_ref="action:betrayal",
        value_ref="value:loyalty",
        appraisal_class="violated",
        alignment=-0.8,
        responsibility=0.9,
        consequence=0.8,
        uncertainty=0.1,
        causal_refs=(
            "experience:betrayal",
        ),
        evidence_refs=(
            "evidence:betrayal",
        ),
    )

    residue = derive_moral_residue(
        appraisal
    )

    assert residue.pressure > 0.0

    assert (
        residue.repair_pressure
        > 0.0
    )

    assert (
        residue.repair_pressure
        <= residue.pressure
    )

    before = residue.pressure

    repair = Repair(
        appraisal_ref=appraisal.id,
        repair_ref="experience:repair",
        acknowledgment=1.0,
        restitution=0.7,
        changed_behavior=0.8,
        acceptance=0.5,
        causal_refs=(
            "commitment:repair",
        ),
    )

    repaired = apply_repair(
        residue,
        repair,
    )

    assert (
        repaired.pressure
        < before
    )

    assert (
        "experience:betrayal"
        in repaired.causal_refs
    )

    assert (
        appraisal.id
        in repaired.causal_refs
    )

    assert (
        "experience:repair"
        in repaired.causal_refs
    )

    assert (
        "commitment:repair"
        in repaired.causal_refs
    )

    assert math.isclose(
        repaired.uncertainty,
        residue.uncertainty,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    projection = (
        conscience_projection(
            appraisal,
            repaired,
            repairs=(repair,),
        )
    )

    assert (
        projection[
            "repair_erased_history"
        ]
        is False
    )

    assert (
        projection[
            "external_authority_upgraded"
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
        appraisal.projection()[
            "authority_effect"
        ]
        == "none"
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
