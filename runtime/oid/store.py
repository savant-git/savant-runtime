from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3
from typing import Any, Mapping, Sequence

from runtime.oid.core import TemporalRecord
from runtime.oid.frame import OidFrame


SCHEMA = "savant://oid/store/1"


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    artifact_id: str
    artifact_type: str
    frame_ref: str
    generation: int | None
    payload: Mapping[str, Any]


class OidStore:
    def __init__(
        self,
        path: str | Path,
    ) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.path),
            isolation_level=None,
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        connection.execute(
            "PRAGMA journal_mode = WAL"
        )
        connection.execute(
            "PRAGMA synchronous = FULL"
        )

        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS
                oid_artifact (
                    artifact_id TEXT PRIMARY KEY,
                    artifact_type TEXT NOT NULL,
                    frame_ref TEXT NOT NULL,
                    generation INTEGER,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS
                oid_artifact_frame_generation
                ON oid_artifact(
                    frame_ref,
                    generation
                );

                CREATE TABLE IF NOT EXISTS
                oid_lineage (
                    successor_ref TEXT PRIMARY KEY,
                    predecessor_ref TEXT NOT NULL,
                    frame_ref TEXT NOT NULL,
                    successor_generation INTEGER NOT NULL,
                    FOREIGN KEY(successor_ref)
                        REFERENCES oid_artifact(
                            artifact_id
                        )
                );

                CREATE INDEX IF NOT EXISTS
                oid_lineage_predecessor
                ON oid_lineage(
                    predecessor_ref
                );
                """
            )

    @staticmethod
    def _payload(
        projection: Mapping[str, Any],
    ) -> str:
        return json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def put_record(
        self,
        record: TemporalRecord,
    ) -> None:
        projection = record.projection()

        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")

            connection.execute(
                """
                INSERT OR IGNORE INTO oid_artifact(
                    artifact_id,
                    artifact_type,
                    frame_ref,
                    generation,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    "record",
                    record.frame_ref,
                    None,
                    self._payload(projection),
                ),
            )

            row = connection.execute(
                """
                SELECT payload_json
                FROM oid_artifact
                WHERE artifact_id = ?
                """,
                (record.id,),
            ).fetchone()

            if (
                row is None
                or row[0]
                != self._payload(projection)
            ):
                connection.rollback()
                raise ValueError(
                    "oid record integrity conflict"
                )

            connection.commit()

    def put_frame(
        self,
        frame: OidFrame,
    ) -> None:
        projection = frame.projection()

        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")

            for record in frame.records:
                record_projection = (
                    record.projection()
                )

                connection.execute(
                    """
                    INSERT OR IGNORE INTO oid_artifact(
                        artifact_id,
                        artifact_type,
                        frame_ref,
                        generation,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        "record",
                        record.frame_ref,
                        None,
                        self._payload(
                            record_projection
                        ),
                    ),
                )

            connection.execute(
                """
                INSERT OR IGNORE INTO oid_artifact(
                    artifact_id,
                    artifact_type,
                    frame_ref,
                    generation,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    frame.id,
                    "frame",
                    frame.frame_ref,
                    frame.generation,
                    self._payload(projection),
                ),
            )

            row = connection.execute(
                """
                SELECT payload_json
                FROM oid_artifact
                WHERE artifact_id = ?
                """,
                (frame.id,),
            ).fetchone()

            if (
                row is None
                or row[0]
                != self._payload(projection)
            ):
                connection.rollback()
                raise ValueError(
                    "oid frame integrity conflict"
                )

            if frame.predecessor_ref is not None:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO oid_lineage(
                        successor_ref,
                        predecessor_ref,
                        frame_ref,
                        successor_generation
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        frame.id,
                        frame.predecessor_ref,
                        frame.frame_ref,
                        frame.generation,
                    ),
                )

                lineage = connection.execute(
                    """
                    SELECT
                        predecessor_ref,
                        frame_ref,
                        successor_generation
                    FROM oid_lineage
                    WHERE successor_ref = ?
                    """,
                    (frame.id,),
                ).fetchone()

                expected = (
                    frame.predecessor_ref,
                    frame.frame_ref,
                    frame.generation,
                )

                if lineage != expected:
                    connection.rollback()
                    raise ValueError(
                        "oid lineage integrity conflict"
                    )

            connection.commit()

    def get(
        self,
        artifact_id: str,
    ) -> StoredArtifact | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    artifact_id,
                    artifact_type,
                    frame_ref,
                    generation,
                    payload_json
                FROM oid_artifact
                WHERE artifact_id = ?
                """,
                (artifact_id,),
            ).fetchone()

        if row is None:
            return None

        return StoredArtifact(
            artifact_id=row[0],
            artifact_type=row[1],
            frame_ref=row[2],
            generation=row[3],
            payload=json.loads(row[4]),
        )

    def frame_history(
        self,
        frame_ref: str,
    ) -> tuple[StoredArtifact, ...]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    artifact_id,
                    artifact_type,
                    frame_ref,
                    generation,
                    payload_json
                FROM oid_artifact
                WHERE
                    frame_ref = ?
                    AND artifact_type = 'frame'
                ORDER BY
                    generation ASC,
                    artifact_id ASC
                """,
                (frame_ref,),
            ).fetchall()

        return tuple(
            StoredArtifact(
                artifact_id=row[0],
                artifact_type=row[1],
                frame_ref=row[2],
                generation=row[3],
                payload=json.loads(row[4]),
            )
            for row in rows
        )

    def validate_lineage(
        self,
        frame_ref: str,
    ) -> bool:
        history = self.frame_history(
            frame_ref
        )

        if not history:
            return True

        generations = [
            item.generation
            for item in history
        ]

        if generations != list(
            range(len(history))
        ):
            return False

        with self.connect() as connection:
            for index in range(
                1,
                len(history),
            ):
                current = history[index]
                previous = history[index - 1]

                row = connection.execute(
                    """
                    SELECT predecessor_ref
                    FROM oid_lineage
                    WHERE successor_ref = ?
                    """,
                    (
                        current.artifact_id,
                    ),
                ).fetchone()

                if (
                    row is None
                    or row[0]
                    != previous.artifact_id
                ):
                    return False

        return True

    def projection(
        self,
        frame_ref: str,
    ) -> Mapping[str, Any]:
        history = self.frame_history(
            frame_ref
        )

        return {
            "schema": SCHEMA,
            "frame_ref": frame_ref,
            "frame_count": len(history),
            "frame_refs": [
                item.artifact_id
                for item in history
            ],
            "lineage_valid": (
                self.validate_lineage(
                    frame_ref
                )
            ),
            "append_only_identity": True,
            "transactional": True,
            "wal_enabled": True,
            "authority_transferred": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }
