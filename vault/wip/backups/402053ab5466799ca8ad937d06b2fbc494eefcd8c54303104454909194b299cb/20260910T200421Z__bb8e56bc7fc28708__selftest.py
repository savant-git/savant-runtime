import sys

sys.path.insert(0, "/root/savant-runtime")

from runtime.glyph.composition import GlyphRegistry
from runtime.noumenon.appraisal import (
    appraisal_from_projection,
    build_transition_candidate,
    eligible_for_development,
)
from runtime.noumenon.integrant import (
    candidate,
    consume,
    emit,
    request,
)
from runtime.noumenon.state import (
    Experience,
    continuity_receipt,
    empty_state,
)


def main() -> int:
    registry = GlyphRegistry()

    source = "noumenon"
    composition = registry.decompose_text(source)

    assert registry.materialize(composition) == source
    assert len(registry.values()) < len(source)

    before = empty_state("selftest")

    experience = Experience(
        id="experience:selftest",
        observed=True,
        owned=True,
    )

    incoming = consume(
        "palaver",
        "experience_candidate",
        experience.projection(),
        evidence_refs=("evidence:selftest",),
    )

    assert incoming.projection()["integrant"] == "numinon"
    assert incoming.target == "noumenon"
    assert incoming.direction == "consume"

    cognitive_request = request(
        "opus",
        "noumenon.appraise",
        {
            "experience_id": experience.id,
            "state_digest": before.state_digest,
        },
        lineage_refs=(before.noumenon_id,),
    )

    assert cognitive_request.target == "opus"
    assert cognitive_request.direction == "request"

    cognitive_candidate = candidate(
        "opus",
        "noumenon.appraise",
        {
            "significance_dimensions": {
                "personal": 0.5,
            },
            "uncertainty": {
                "personal": 0.2,
            },
            "consequence_dimensions": {
                "trust": 0.1,
            },
            "interpretation_refs": [
                "interpretation:selftest",
            ],
        },
        evidence_refs=("evidence:selftest",),
        lineage_refs=(before.noumenon_id,),
    )

    appraisal = appraisal_from_projection(
        experience,
        cognitive_candidate.payload,
        causal_refs=(
            experience.id,
            cognitive_candidate.id,
        ),
    )

    assert eligible_for_development(appraisal)

    transition = build_transition_candidate(
        before,
        appraisal,
    )

    assert transition is not None

    after = transition.successor()

    assert after.generation == 1
    assert after.dimensions["trust"] == 0.1

    relationship_output = emit(
        "rapport",
        "relationship_consequence_candidate",
        {
            "noumenon_id": after.noumenon_id,
            "dimension": "trust",
            "delta": 0.1,
        },
        lineage_refs=after.lineage_refs,
    )

    assert relationship_output.target == "rapport"
    assert relationship_output.direction == "emit"
    assert (
        relationship_output.projection()[
            "authority_transfer"
        ]
        is False
    )

    receipt = continuity_receipt(
        before,
        after,
        transition_refs=after.lineage_refs,
        evidence_refs=("evidence:selftest",),
    )

    assert receipt["integrity_digest"]
    assert (
        receipt["successor_id"]
        == after.noumenon_id
    )

    rejected_experience = Experience(
        id="experience:unowned",
        observed=True,
        owned=False,
    )

    rejected_appraisal = appraisal_from_projection(
        rejected_experience,
        {
            "significance_dimensions": {
                "personal": 1.0,
            },
            "uncertainty": {},
            "consequence_dimensions": {
                "trust": 1.0,
            },
            "interpretation_refs": [],
        },
        causal_refs=(
            rejected_experience.id,
        ),
    )

    assert not eligible_for_development(
        rejected_appraisal
    )

    assert (
        build_transition_candidate(
            before,
            rejected_appraisal,
        )
        is None
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
