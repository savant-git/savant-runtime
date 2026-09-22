import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
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
from runtime.oid.recovery import (
    inspect_recovery,
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
        frame_ref="oid:recovery-test",
        source_clock_ref="clock:a",
        logical_sequence=0,
        event_interval=TemporalInterval(
            start=base,
            end=base + timedelta(seconds=1),
        ),
        observation_time=(
            base + timedelta(seconds=2)
        ),
    )

    genesis = establish_frame(
        "oid:recovery-test",
        (first,),
        causal_refs=("source:genesis",),
    )

    second = TemporalRecord(
        record_ref="event:b",
        frame_ref="oid:recovery-test",
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
    )

    successor, _ = advance_frame(
        genesis,
        (first, second),
        causal_refs=("source:advance",),
    )

    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "oid.sqlite3"

        store = OidStore(path)
        store.initialize()

        store.put_frame(genesis)
        store.put_frame(successor)

        clean = inspect_recovery(
            store,
            "oid:recovery-test",
        )

        assert clean.issues == ()
        assert clean.lineage_valid is True

        assert (
            clean.latest_valid_ref
            == successor.id
        )

        assert (
            clean.latest_valid_generation
            == 1
        )

        projection = clean.projection()

        assert (
            projection["destructive_repair"]
            is False
        )

        assert (
            projection[
                "historical_state_preserved"
            ]
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

        with sqlite3.connect(
            str(path)
        ) as connection:
            connection.execute(
                """
                UPDATE oid_artifact
                SET payload_json = ?
                WHERE artifact_id = ?
                """,
                (
                    '{"digest":"corrupt"}',
                    successor.id,
                ),
            )
            connection.commit()

        damaged = inspect_recovery(
            store,
            "oid:recovery-test",
        )

        assert any(
            issue.issue == "digest_mismatch"
            for issue in damaged.issues
        )

        assert (
            damaged.latest_valid_ref
            == genesis.id
        )

        assert (
            damaged.latest_valid_generation
            == 0
        )

        assert all(
            issue.projection()[
                "automatic_mutation"
            ]
            is False
            for issue in damaged.issues
        )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
