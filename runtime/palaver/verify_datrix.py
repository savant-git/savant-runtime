from __future__ import annotations

import sys
import tempfile
from pathlib import Path

palaver_runtime = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/palaver/runtime"
)

sys.path.insert(
    0,
    str(palaver_runtime),
)

from conversation_transport import (
    conversation_event_buffer,
)
from sequence_recovery import (
    restore_bounded_history,
)
from session_store import (
    session_store,
)


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        datrix_path = (
            Path(directory)
            / "palaver-test.datrix"
        )

        session = (
            "palses_datrix_functional_check"
        )

        store = session_store(
            datrix_path
        )

        store.ensure_session(
            session
        )

        buffer = conversation_event_buffer(
            session=session,
            maximum_events=16,
        )

        first = buffer.publish(
            request="palreq_1",
            kind="session.state",
            payload={
                "value": 1,
                "authority_effect": "none",
            },
        )

        second = buffer.publish(
            request="palreq_2",
            kind="session.state",
            payload={
                "value": 2,
                "authority_effect": "none",
            },
        )

        assert store.persist_event(
            first
        )

        assert store.persist_event(
            second
        )

        store.record_receipt(
            receipt_id="palrec_1",
            session=session,
            request="palreq_2",
            receipt_type="functional_check",
            receipt_owner="exile:palaver",
            payload={
                "verified": True,
            },
        )

        store.close()

        reopened = session_store(
            datrix_path
        )

        persisted = reopened.load_events(
            session,
            limit=16,
        )

        assert len(persisted) == 2
        assert persisted[0].sequence == 1
        assert persisted[1].sequence == 2

        assert (
            persisted[0].semantic_digest
            == first.semantic_digest
        )

        assert (
            persisted[1].semantic_digest
            == second.semantic_digest
        )

        receipts = reopened.receipts(
            session
        )

        assert len(receipts) == 1

        assert (
            receipts[0]["receipt_id"]
            == "palrec_1"
        )

        recovered_buffer = (
            conversation_event_buffer(
                session=session,
                maximum_events=16,
            )
        )

        recovery = restore_bounded_history(
            store=reopened,
            buffer=recovered_buffer,
            session=session,
            capacity=16,
        )

        assert (
            recovered_buffer.latest_sequence
            == 2
        )

        assert (
            recovery["total_events"]
            == 2
        )

        assert (
            recovery["latest_sequence"]
            == 2
        )

        projection = (
            reopened.recovery_projection(
                session
            )
        )

        assert projection is not None

        assert (
            projection["event_count"]
            == 2
        )

        assert (
            projection["receipt_count"]
            == 1
        )

        assert (
            projection["latest_sequence"]
            == 2
        )

        reopened.close()

        print(
            "datrix:",
            datrix_path,
        )

        print(
            "events:",
            len(persisted),
        )

        print(
            "receipts:",
            len(receipts),
        )

        print(
            "latest_sequence:",
            recovery[
                "latest_sequence"
            ],
        )

        print(
            "deterministic_replay:",
            True,
        )

        print(
            "bounded_recovery:",
            True,
        )

        print(
            "focused_functional_check: PASS"
        )


if __name__ == "__main__":
    main()
