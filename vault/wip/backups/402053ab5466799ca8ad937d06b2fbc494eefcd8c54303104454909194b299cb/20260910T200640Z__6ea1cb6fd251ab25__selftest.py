import sys

sys.path.insert(0, "/root/savant-runtime")

from runtime.glyph.composition import GlyphRegistry
from runtime.noumenon.admission import (
    admit_transition,
    candidate_digest,
    evaluate_admission,
    notary_admission_payload,
)
from runtime.noumenon.appraisal import (
    appraisal_from_projection,
    build_transition_candidate,
    eligible_for_development,
)
from runtime.noumenon.bridges import (
    carbon_counterlife_request,
    guise_character_projection,
    memory_significance_candidate,
    opus_appraisal_request,
    rapport_consequence_candidate,
    underscore_divergence_request,
)
from runtime.noumenon.integrant import (
    candidate,
    consume,
)
from runtime.noumenon.state import (
    Experience,
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

    character = guise_character_projection(
        {
            "character_id": "character:selftest",
            "traits": {},
            "unknowns": ["all_unsubstantiated"],
        },
        evidence_refs=("evidence:character",),
    )

    assert character.source == "guise"
    assert character.target == "noumenon"

    cognitive_request = opus_appraisal_request(
        before,
        experience_id=experience.id,
        context_refs=(character.id,),
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

    digest = candidate_digest(transition)

    notary = candidate(
        "notary",
        "noumenon.admission",
        notary_admission_payload(
            transition,
            admitted=True,
            reason="selftest",
        ),
        authority_refs=("authority:selftest",),
        evidence_refs=("evidence:selftest",),
        lineage_refs=(digest,),
    )

    decision = evaluate_admission(
        transition,
        notary_envelope=notary,
    )

    assert decision.admitted

    admitted = admit_transition(
        transition,
        decision,
    )

    after = admitted.successor

    assert after.generation == 1
    assert after.dimensions["trust"] == 0.1
    assert admitted.receipt["integrity_digest"]

    rapport_output = rapport_consequence_candidate(
        after,
        {
            "dimension": "trust",
            "delta": 0.1,
        },
    )

    assert rapport_output.target == "rapport"

    memory_output = memory_significance_candidate(
        after,
        memory_ref="memory:selftest",
        significance=0.5,
    )

    assert memory_output.target == "memory"

    divergence = underscore_divergence_request(
        after,
        candidate_refs=(
            cognitive_candidate.id,
        ),
    )

    assert divergence.target == "underscore"

    counterlife = carbon_counterlife_request(
        after,
        fork_ref=experience.id,
        excluded_event_refs=(experience.id,),
    )

    assert counterlife.target == "carbon"
    assert (
        counterlife.payload["authoritative"]
        is False
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

    false_notary = candidate(
        "notary",
        "noumenon.admission",
        {
            "admitted": True,
            "candidate_digest": "wrong",
        },
    )

    rejected = evaluate_admission(
        transition,
        notary_envelope=false_notary,
    )

    assert not rejected.admitted
    assert (
        rejected.reason
        == "candidate_digest_mismatch"
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
