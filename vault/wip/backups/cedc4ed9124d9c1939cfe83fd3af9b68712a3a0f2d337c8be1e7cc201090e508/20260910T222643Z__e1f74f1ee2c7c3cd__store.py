from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from runtime.noumenon.admission import (
    AdmittedTransition,
    AdmissionDecision,
)
from runtime.noumenon.state import NoumenonState


SCHEMA = "savant://noumenon/store/2"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _state_from_projection(
    projection: Mapping[str, Any],
) -> NoumenonState:
    return NoumenonState(
        noumenon_id=str(
            projection["noumenon_id"]
        ),
        predecessor_id=(
            str(projection["predecessor_id"])
            if projection.get(
                "predecessor_id"
            )
            is not None
            else None
        ),
        succession_status=str(
            projection[
                "succession_status"
            ]
        ),
        generation=int(
            projection["generation"]
        ),
        dimensions={
            str(key): float(value)
            for key, value
            in dict(
                projection.get(
                    "dimensions",
                    {},
                )
            ).items()
        },
        unresolved=tuple(
            str(value)
            for value
            in projection.get(
                "unresolved",
                [],
            )
        ),
        lineage_refs=tuple(
            str(value)
            for value
            in projection.get(
                "lineage_refs",
                [],
            )
        ),
        relationship_refs=tuple(
            str(value)
            for value
            in projection.get(
                "relationship_refs",
                [],
            )
        ),
        memory_refs=tuple(
            str(value)
            for value
            in projection.get(
                "memory_refs",
                [],
            )
        ),
        value_refs=tuple(
            str(value)
            for value
            in projection.get(
                "value_refs",
                [],
            )
        ),
    )


class NoumenonStore:
    def __init__(
        self,
        path: str | Path,
    ) -> None:
        self.path = Path(path)

    def connect(
        self,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.path)
        )

        connection.row_factory = (
            sqlite3.Row
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.connect() as connection:
            connection.execute(
                "PRAGMA journal_mode = WAL"
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS states (
                    state_digest TEXT PRIMARY KEY,
                    noumenon_id TEXT NOT NULL,
                    predecessor_id TEXT,
                    generation INTEGER NOT NULL,
                    succession_status TEXT NOT NULL,
                    projection_json TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                states_noumenon_generation
                ON states (
                    noumenon_id,
                    generation
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS admissions (
                    decision_digest TEXT PRIMARY KEY,
                    candidate_digest TEXT NOT NULL,
                    predecessor_digest TEXT NOT NULL,
                    admitted INTEGER NOT NULL,
                    decision_json TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS receipts (
                    integrity_digest TEXT PRIMARY KEY,
                    predecessor_id TEXT NOT NULL,
                    successor_id TEXT NOT NULL,
                    receipt_json TEXT NOT NULL
                )
                """
            )

    def _append_state(
        self,
        connection: sqlite3.Connection,
        state: NoumenonState,
    ) -> None:
        projection = state.projection()
        encoded = _canonical_json(
            projection
        )

        existing = connection.execute(
            """
            SELECT projection_json
            FROM states
            WHERE state_digest = ?
            """,
            (
                state.state_digest,
            ),
        ).fetchone()

        if existing is not None:
            if (
                existing[
                    "projection_json"
                ]
                != encoded
            ):
                raise ValueError(
                    "immutable state collision"
                )

            return

        connection.execute(
            """
            INSERT INTO states (
                state_digest,
                noumenon_id,
                predecessor_id,
                generation,
                succession_status,
                projection_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                state.state_digest,
                state.noumenon_id,
                state.predecessor_id,
                state.generation,
                state.succession_status,
                encoded,
            ),
        )

    def append_state(
        self,
        state: NoumenonState,
    ) -> None:
        if state.generation != 0:
            raise ValueError(
                "post-genesis states require "
                "an admitted transition"
            )

        if state.predecessor_id is not None:
            raise ValueError(
                "genesis state cannot have "
                "a predecessor"
            )

        with self.connect() as connection:
            self._append_state(
                connection,
                state,
            )

    def _append_admission(
        self,
        connection: sqlite3.Connection,
        decision: AdmissionDecision,
    ) -> None:
        projection = (
            decision.projection()
        )

        encoded = _canonical_json(
            projection
        )

        existing = connection.execute(
            """
            SELECT decision_json
            FROM admissions
            WHERE decision_digest = ?
            """,
            (
                decision.digest,
            ),
        ).fetchone()

        if existing is not None:
            if (
                existing[
                    "decision_json"
                ]
                != encoded
            ):
                raise ValueError(
                    "immutable admission "
                    "collision"
                )

            return

        connection.execute(
            """
            INSERT INTO admissions (
                decision_digest,
                candidate_digest,
                predecessor_digest,
                admitted,
                decision_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                decision.digest,
                decision.candidate_digest,
                decision.predecessor_digest,
                1
                if decision.admitted
                else 0,
                encoded,
            ),
        )

    def _append_receipt(
        self,
        connection: sqlite3.Connection,
        receipt: Mapping[str, Any],
    ) -> None:
        integrity_digest = str(
            receipt[
                "integrity_digest"
            ]
        )

        predecessor_id = str(
            receipt["predecessor_id"]
        )

        successor_id = str(
            receipt["successor_id"]
        )

        encoded = _canonical_json(
            dict(receipt)
        )

        existing = connection.execute(
            """
            SELECT receipt_json
            FROM receipts
            WHERE integrity_digest = ?
            """,
            (
                integrity_digest,
            ),
        ).fetchone()

        if existing is not None:
            if (
                existing[
                    "receipt_json"
                ]
                != encoded
            ):
                raise ValueError(
                    "immutable receipt collision"
                )

            return

        connection.execute(
            """
            INSERT INTO receipts (
                integrity_digest,
                predecessor_id,
                successor_id,
                receipt_json
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                integrity_digest,
                predecessor_id,
                successor_id,
                encoded,
            ),
        )

    def append_receipt(
        self,
        receipt: Mapping[str, Any],
    ) -> None:
        with self.connect() as connection:
            self._append_receipt(
                connection,
                receipt,
            )

    def append_admitted_transition(
        self,
        admitted: AdmittedTransition,
    ) -> None:
        decision = admitted.decision

        if not decision.admitted:
            raise ValueError(
                "transition was not admitted"
            )

        predecessor = (
            admitted.predecessor
        )

        successor = admitted.successor

        if (
            successor.noumenon_id
            != predecessor.noumenon_id
        ):
            raise ValueError(
                "admitted transition changed "
                "noumenon identity"
            )

        if (
            successor.predecessor_id
            != predecessor.state_digest
        ):
            raise ValueError(
                "admitted transition has "
                "invalid predecessor"
            )

        if (
            successor.generation
            != predecessor.generation + 1
        ):
            raise ValueError(
                "admitted transition has "
                "invalid generation"
            )

        if (
            decision.predecessor_digest
            != predecessor.state_digest
        ):
            raise ValueError(
                "admission predecessor "
                "does not match transition"
            )

        with self.connect() as connection:
            existing_predecessor = (
                connection.execute(
                    """
                    SELECT state_digest
                    FROM states
                    WHERE state_digest = ?
                    """,
                    (
                        predecessor.state_digest,
                    ),
                ).fetchone()
            )

            if (
                existing_predecessor
                is None
            ):
                raise ValueError(
                    "predecessor state is "
                    "not persisted"
                )

            self._append_admission(
                connection,
                decision,
            )

            self._append_state(
                connection,
                successor,
            )

            self._append_receipt(
                connection,
                admitted.receipt,
            )

    def load_state(
        self,
        state_digest: str,
    ) -> NoumenonState | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT projection_json
                FROM states
                WHERE state_digest = ?
                """,
                (
                    state_digest,
                ),
            ).fetchone()

        if row is None:
            return None

        projection = json.loads(
            row["projection_json"]
        )

        state = _state_from_projection(
            projection
        )

        if (
            state.state_digest
            != state_digest
        ):
            raise ValueError(
                "persisted state failed "
                "integrity verification"
            )

        return state

    def load_receipt(
        self,
        integrity_digest: str,
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT receipt_json
                FROM receipts
                WHERE integrity_digest = ?
                """,
                (
                    integrity_digest,
                ),
            ).fetchone()

        if row is None:
            return None

        receipt = json.loads(
            row["receipt_json"]
        )

        if (
            receipt.get(
                "integrity_digest"
            )
            != integrity_digest
        ):
            raise ValueError(
                "persisted receipt failed "
                "identity verification"
            )

        return receipt

    def load_admission(
        self,
        decision_digest: str,
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT decision_json
                FROM admissions
                WHERE decision_digest = ?
                """,
                (
                    decision_digest,
                ),
            ).fetchone()

        if row is None:
            return None

        return json.loads(
            row["decision_json"]
        )

    def lineage(
        self,
        noumenon_id: str,
    ) -> tuple[NoumenonState, ...]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT projection_json
                FROM states
                WHERE noumenon_id = ?
                ORDER BY generation ASC
                """,
                (
                    noumenon_id,
                ),
            ).fetchall()

        states = tuple(
            _state_from_projection(
                json.loads(
                    row["projection_json"]
                )
            )
            for row in rows
        )

        for state in states:
            if (
                state.noumenon_id
                != noumenon_id
            ):
                raise ValueError(
                    "persisted lineage identity "
                    "mismatch"
                )

        return states
