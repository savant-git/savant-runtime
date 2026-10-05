import sys
import tempfile
from pathlib import Path

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
from runtime.noumenon.development import (
    MeaningLayer,
    SelfExplanation,
    continuity_challenge,
    counterlife_comparison,
    metrics,
    reinterpret,
)
from runtime.noumenon.integrant import (
    candidate,
    consume,
)
from runtime.noumenon.state import (
    Experience,
    empty_state,
)
from runtime.noumenon.store import NoumenonStore


def main() -> int:
    registry = GlyphRegistry()

    source = "noumenon"
    composition = registry.decompose_text(source)

    assert registry.materialize(
        composition
    ) == source

    assert len(
        registry.values()
    ) < len(source)

    before = empty_state(
        "selftest"
    )

    experience = Experience(
        id="experience:selftest",
        observed=True,
        owned=True,
    )

    incoming = consume(
        "palaver",
        "experience_candidate",
        experience.projection(),
        evidence_refs=(
            "evidence:selftest",
        ),
    )

    incoming_projection = (
        incoming.projection()
    )

    assert (
        incoming_projection[
            "integrant"
        ]
        == "noumenon"
    )

    assert (
        incoming.target
        == "noumenon"
    )

    character = guise_character_projection(
        {
            "character_id": (
                "character:selftest"
            ),
            "traits": {},
            "unknowns": [
                "all_unsubstantiated"
            ],
        },
        evidence_refs=(
            "evidence:character",
        ),
    )

    assert (
        character.target
        == "noumenon"
    )

    cognitive_request = (
        opus_appraisal_request(
            before,
            experience_id=(
                experience.id
            ),
            context_refs=(
                character.id,
            ),
        )
    )

    assert (
        cognitive_request.source
        == "noumenon"
    )

    assert (
        cognitive_request.target
        == "opus"
    )

    cognitive_candidate = candidate(
        "opus",
        "noumenon.appraise",
        {
            "state_digest": (
                before.state_digest
            ),
            "significance_dimensions": {
                "personal": 0.5
            },
            "uncertainty": {
                "personal": 0.2
            },
            "consequence_dimensions": {
                "trust": 0.1
            },
            "interpretation_refs": [
                "interpretation:selftest"
            ],
        },
        evidence_refs=(
            "evidence:selftest",
        ),
        lineage_refs=(
            before.noumenon_id,
        ),
    )

    assert (
        cognitive_candidate.target
        == "noumenon"
    )

    appraisal = (
        appraisal_from_projection(
            experience,
            cognitive_candidate.payload,
            causal_refs=(
                experience.id,
                cognitive_candidate.id,
            ),
        )
    )

    assert eligible_for_development(
        appraisal
    )

    transition = (
        build_transition_candidate(
            before,
            appraisal,
        )
    )

    assert transition is not None

    digest = candidate_digest(
        transition
    )

    notary = candidate(
        "notary",
        "noumenon.admission",
        notary_admission_payload(
            transition,
            admitted=True,
            reason="selftest",
        ),
        authority_refs=(
            "authority:selftest",
        ),
        evidence_refs=(
            "evidence:selftest",
        ),
        lineage_refs=(
            digest,
        ),
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

    challenge = continuity_challenge(
        before,
        after,
    )

    assert challenge["continuous"]

    developmental_metrics = metrics(
        before,
        after,
    )

    assert (
        developmental_metrics.velocity[
            "trust"
        ]
        == 0.1
    )

    first_meaning = MeaningLayer(
        event_ref=experience.id,
        interpretation_ref=(
            "interpretation:first"
        ),
        significance={
            "personal": 0.5
        },
        uncertainty={
            "personal": 0.2
        },
    )

    revised_meaning = reinterpret(
        first_meaning,
        interpretation_ref=(
            "interpretation:revised"
        ),
        significance={
            "personal": 0.3
        },
        uncertainty={
            "personal": 0.4
        },
    )

    assert (
        revised_meaning.predecessor_ref
        == first_meaning.id
    )

    explanation = SelfExplanation(
        state_digest=(
            after.state_digest
        ),
        claim=(
            "the experience may have "
            "affected trust"
        ),
        confidence=0.6,
        evidence_refs=(
            experience.id,
        ),
        alternatives=(
            "another cause may contribute",
        ),
    )

    assert (
        explanation.projection()[
            "authoritative_causal_access"
        ]
        is False
    )

    counterlife = (
        counterlife_comparison(
            after,
            {
                "trust": 0.0
            },
            fork_ref=experience.id,
            simulation_ref=(
                "simulation:selftest"
            ),
        )
    )

    assert (
        counterlife["authoritative"]
        is False
    )

    rapport_output = (
        rapport_consequence_candidate(
            after,
            {
                "dimension": "trust",
                "delta": 0.1,
            },
        )
    )

    assert (
        rapport_output.source
        == "noumenon"
    )

    assert (
        rapport_output.target
        == "rapport"
    )

    memory_output = (
        memory_significance_candidate(
            after,
            memory_ref=(
                "memory:selftest"
            ),
            significance=0.5,
        )
    )

    assert (
        memory_output.source
        == "noumenon"
    )

    assert (
        memory_output.target
        == "memory"
    )

    divergence = (
        underscore_divergence_request(
            after,
            candidate_refs=(
                cognitive_candidate.id,
            ),
        )
    )

    assert (
        divergence.source
        == "noumenon"
    )

    assert (
        divergence.target
        == "underscore"
    )

    counterlife_request = (
        carbon_counterlife_request(
            after,
            fork_ref=experience.id,
            excluded_event_refs=(
                experience.id,
            ),
        )
    )

    assert (
        counterlife_request.source
        == "noumenon"
    )

    assert (
        counterlife_request.target
        == "carbon"
    )

    with tempfile.TemporaryDirectory() as root:
        database = (
            Path(root)
            / "noumenon.sqlite3"
        )

        store = NoumenonStore(
            database
        )

        store.initialize()

        store.append_state(
            before
        )

        store.append_state(
            after
        )

        store.append_receipt(
            admitted.receipt
        )

        restored = store.load_state(
            after.state_digest
        )

        assert restored is not None

        assert (
            restored.state_digest
            == after.state_digest
        )

        restored_receipt = (
            store.load_receipt(
                admitted.receipt[
                    "integrity_digest"
                ]
            )
        )

        assert (
            restored_receipt
            is not None
        )

    rejected_experience = Experience(
        id="experience:unowned",
        observed=True,
        owned=False,
    )

    rejected_appraisal = (
        appraisal_from_projection(
            rejected_experience,
            {
                "significance_dimensions": {
                    "personal": 1.0
                },
                "uncertainty": {},
                "consequence_dimensions": {
                    "trust": 1.0
                },
                "interpretation_refs": [],
            },
            causal_refs=(
                rejected_experience.id,
            ),
        )
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
            "candidate_digest": (
                "wrong"
            ),
        },
    )

    rejected = evaluate_admission(
        transition,
        notary_envelope=(
            false_notary
        ),
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
