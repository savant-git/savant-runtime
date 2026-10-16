import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

sys.path.insert(
    0,
    "/root/savant-runtime",
)

from runtime.oid.core import (
    TemporalInterval,
    TemporalRecord,
)
from runtime.oid.frame import (
    advance_frame,
    establish_frame,
)
from runtime.oid.store import OidStore


def main() -> int:
    base = datetime(
        2026,
        9,
        11,
        0,
        0,
        tzinfo=timezone.utc,
    )

    first = TemporalRecord(
        record_ref="event:a",
        frame_ref="oid:persistence-test",
        source_clock_ref="clock:a",
        logical_sequence=0,
        event_interval=TemporalInterval(
            start=base,
            end=base + timedelta(seconds=1),
        ),
        observation_time=(
            base + timedelta(seconds=2)
        ),
        evidence_refs=("evidence:a",),
    )

    genesis = establish_frame(
        "oid:persistence-test",
        (first,),
        causal_refs=("source:genesis",),
    )

    second = TemporalRecord(
        record_ref="event:b",
        frame_ref="oid:persistence-test",
        source_clock_ref="clock:b",
        logical_sequence=1,
        event_interval=TemporalInterval(
            start=base + timedelta(seconds=3),
            end=base + timedelta(seconds=4),
        ),
        observation_time=(
            base + timedelta(seconds=5)
        ),
        predecessor_refs=(first.id,),
        evidence_refs=("evidence:b",),
    )

    successor, _ = advance_frame(
        genesis,
        (
            first,
            second,
        ),
        causal_refs=("source:successor",),
    )

    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "oid.sqlite3"

        store = OidStore(path)
        store.initialize()

        store.put_frame(genesis)
        store.put_frame(successor)

        loaded = store.get(successor.id)

        assert loaded is not None
        assert loaded.artifact_type == "frame"

        assert (
            loaded.payload["digest"]
            == successor.digest
        )

        history = store.frame_history(
            "oid:persistence-test"
        )

        assert len(history) == 2

        assert history[0].generation == 0
        assert history[1].generation == 1

        assert (
            history[0].artifact_id
            == genesis.id
        )

        assert (
            history[1].artifact_id
            == successor.id
        )

        assert store.validate_lineage(
            "oid:persistence-test"
        )

        projection = store.projection(
            "oid:persistence-test"
        )

        assert (
            projection["lineage_valid"]
            is True
        )

        assert (
            projection[
                "append_only_identity"
            ]
            is True
        )

        assert (
            projection["transactional"]
            is True
        )

        assert (
            projection["wal_enabled"]
            is True
        )

        assert (
            projection[
                "authority_transferred"
            ]
            is False
        )

        assert (
            projection["authoritative"]
            is False
        )

        assert (
            projection["authority_effect"]
            == "none"
        )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
