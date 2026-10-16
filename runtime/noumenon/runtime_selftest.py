import tempfile
import sys

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.admission import (
    candidate_digest,
)
from runtime.noumenon.integrant import (
    candidate as integrant_candidate,
)
from runtime.noumenon.runtime import (
    NoumenonRuntime,
    transition_identity,
)
from runtime.noumenon.state import (
    DevelopmentalConsequence,
    Experience,
    Significance,
    TransitionCandidate,
    empty_state,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as root:
        runtime = (
            NoumenonRuntime.from_path(
                root + "/noumenon.sqlite3"
            )
        )

        runtime.initialize()

        genesis = empty_state(
            "runtime-selftest"
        )

        established = runtime.establish(
            genesis
        )

        assert (
            established.state_digest
            == genesis.state_digest
        )

        transition = TransitionCandidate(
            predecessor=genesis,
            experience=Experience(
                id="experience:runtime",
                observed=True,
                owned=True,
                believed=True,
                remembered=True,
            ),
            significance=Significance(
                dimensions={
                    "personal": 0.8,
                }
            ),
            consequences=(
                DevelopmentalConsequence(
                    dimension="trust",
                    delta=0.2,
                    causal_refs=(
                        "experience:runtime",
                    ),
                ),
            ),
        )

        identity = transition_identity(
            transition
        )

        assert (
            identity[
                "predecessor_state_digest"
            ]
            == genesis.state_digest
        )

        digest = candidate_digest(
            transition
        )

        assert (
            identity[
                "candidate_digest"
            ]
            == digest
        )

        request_envelope = (
            runtime.notary_request(
                transition
            )
        )

        assert (
            request_envelope.source
            == "noumenon"
        )

        assert (
            request_envelope.target
            == "notary"
        )

        assert (
            request_envelope.direction
            == "request"
        )

        rejected = runtime.transition(
            transition,
            notary_envelope=None,
        )

        assert not rejected.admitted

        assert (
            rejected.decision.reason
            == "missing_notary_admission"
        )

        assert (
            runtime.current(
                genesis.noumenon_id
            ).state_digest
            == genesis.state_digest
        )

        notary = integrant_candidate(
            "notary",
            (
                "noumenon."
                "transition-admission"
            ),
            {
                "admitted": True,
                "reason": "verified",
                "candidate_digest": digest,
                "predecessor_digest": (
                    genesis.state_digest
                ),
            },
            authority_refs=(
                "authority:selftest",
            ),
            evidence_refs=(
                "evidence:selftest",
            ),
        )

        accepted = runtime.transition(
            transition,
            notary_envelope=notary,
        )

        assert accepted.admitted

        admitted = (
            accepted.admitted_transition
        )

        assert admitted is not None

        assert (
            admitted.successor.noumenon_id
            == genesis.noumenon_id
        )

        assert (
            admitted.successor
            .predecessor_id
            == genesis.state_digest
        )

        current = runtime.current(
            genesis.noumenon_id
        )

        assert current is not None

        assert (
            current.state_digest
            == admitted.successor
            .state_digest
        )

        assert current.generation == 1

        projection = (
            runtime.state_projection(
                current
            )
        )

        assert (
            projection.source
            == "noumenon"
        )

        assert (
            projection.target
            == "memory"
        )

        assert (
            projection.direction
            == "emit"
        )

        status = runtime.status(
            genesis.noumenon_id
        )

        assert (
            status["state_count"]
            == 2
        )

        assert (
            status[
                "current_generation"
            ]
            == 1
        )

        assert not status[
            "ambiguous_current"
        ]

        assert (
            status[
                "branch_generations"
            ]
            == []
        )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
