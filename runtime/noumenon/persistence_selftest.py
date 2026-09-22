import sys
import tempfile
from pathlib import Path

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.noumenon.admission import (
    admit_transition,
    evaluate_admission,
    notary_admission_payload,
)
from runtime.noumenon.integrant import (
    candidate,
)
from runtime.noumenon.state import (
    DevelopmentalConsequence,
    Experience,
    Significance,
    TransitionCandidate,
    empty_state,
)
from runtime.noumenon.store import (
    NoumenonStore,
)


def main() -> int:
    predecessor = empty_state(
        "persistence-selftest"
    )

    transition = TransitionCandidate(
        predecessor=predecessor,
        experience=Experience(
            id="experience:persistence",
            observed=True,
            owned=True,
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
                    "experience:persistence",
                ),
            ),
        ),
    )

    notary = candidate(
        "notary",
        "noumenon.admission",
        notary_admission_payload(
            transition,
            admitted=True,
            reason=(
                "persistence-selftest"
            ),
        ),
        authority_refs=(
            "authority:selftest",
        ),
        evidence_refs=(
            "evidence:selftest",
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

    successor = admitted.successor

    assert (
        successor.noumenon_id
        == predecessor.noumenon_id
    )

    assert (
        successor.predecessor_id
        == predecessor.state_digest
    )

    with tempfile.TemporaryDirectory() as root:
        path = (
            Path(root)
            / "noumenon.sqlite3"
        )

        store = NoumenonStore(
            path
        )

        store.initialize()

        store.append_state(
            predecessor
        )

        bypass_rejected = False

        try:
            store.append_state(
                successor
            )
        except ValueError:
            bypass_rejected = True

        assert bypass_rejected

        store.append_admitted_transition(
            admitted
        )

        restored = store.load_state(
            successor.state_digest
        )

        assert restored is not None

        assert (
            restored.state_digest
            == successor.state_digest
        )

        assert (
            restored.noumenon_id
            == predecessor.noumenon_id
        )

        restored_admission = (
            store.load_admission(
                decision.digest
            )
        )

        assert (
            restored_admission
            is not None
        )

        assert (
            restored_admission[
                "admitted"
            ]
            is True
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

        lineage = store.lineage(
            predecessor.noumenon_id
        )

        assert len(lineage) == 2

        assert (
            lineage[0].state_digest
            == predecessor.state_digest
        )

        assert (
            lineage[1].state_digest
            == successor.state_digest
        )

        assert (
            lineage[0].noumenon_id
            == lineage[1].noumenon_id
        )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
