from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from runtime.noumenon.state import (
    NoumenonState,
)


SCHEMA = "savant://noumenon/store/1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _state_from_projection(
    projection: Mapping[str, Any],
) -> NoumenonState:
    return NoumenonState(
        noumenon_id=str(
            projection["noumenon_id"]
        ),
        predecessor_id=(
            None
            if projection.get(
                "predecessor_id"
            )
            is None
            else str(
                projection["predecessor_id"]
            )
        ),
        succession_status=str(
            projection["succession_status"]
        ),
        generation=int(
            projection["generation"]
        ),
        dimensions={
            str(key): float(value)
            for key, value
            in projection.get(
                "dimensions",
                {},
            ).items()
        },
        unresolved=tuple(
            str(value)
            for value
            in projection.get(
                "unresolved",
                (),
            )
        ),
        lineage_refs=tuple(
            str(value)
            for value
            in projection.get(
                "lineage_refs",
                (),
            )
        ),
        relationship_refs=tuple(
            str(value)
            for value
            in projection.get(
                "relationship_refs",
                (),
            )
        ),
        memory_refs=tuple(
            str(value)
            for value
            in projection.get(
                "memory_refs",
                (),
            )
        ),
        value_refs=tuple(
            str(value)
            for value
            in projection.get(
                "value_refs",
                (),
            )
        ),
    )


class NoumenonStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.path)
        )
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS states (
                    state_digest TEXT PRIMARY KEY,
                    noumenon_id TEXT NOT NULL,
                    predecessor_id TEXT,
                    generation INTEGER NOT NULL,
                    succession_status TEXT NOT NULL,
                    projection_json TEXT NOT NULL,
                    projection_digest TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_noumenon_states_identity_generation
                ON states (
                    noumenon_id,
                    generation
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

    def append_state(
        self,
        state: NoumenonState,
    ) -> str:
        projection = state.projection()
        projection_json = _canonical_json(
            projection
        )
        projection_digest = _digest(
            projection
        )

        if projection_digest != state.state_digest:
            raise ValueError(
                "state projection digest mismatch"
            )

        with self.connect() as connection:
            existing = connection.execute(
                """
                SELECT projection_json
                FROM states
                WHERE state_digest = ?
                """,
                (state.state_digest,),
            ).fetchone()

            if existing is not None:
                if (
                    existing["projection_json"]
                    != projection_json
                ):
                    raise RuntimeError(
                        "immutable state collision"
                    )

                return state.state_digest

            connection.execute(
                """
                INSERT INTO states (
                    state_digest,
                    noumenon_id,
                    predecessor_id,
                    generation,
                    succession_status,
                    projection_json,
                    projection_digest
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.state_digest,
                    state.noumenon_id,
                    state.predecessor_id,
                    state.generation,
                    state.succession_status,
                    projection_json,
                    projection_digest,
                ),
            )

        return state.state_digest

    def append_receipt(
        self,
        receipt: Mapping[str, Any],
    ) -> str:
        integrity_digest = str(
            receipt["integrity_digest"]
        )

        body = dict(receipt)
        supplied = body.pop(
            "integrity_digest"
        )

        expected = _digest(body)

        if supplied != expected:
            raise ValueError(
                "receipt integrity digest mismatch"
            )

        receipt_json = _canonical_json(
            receipt
        )

        with self.connect() as connection:
            existing = connection.execute(
                """
                SELECT receipt_json
                FROM receipts
                WHERE integrity_digest = ?
                """,
                (integrity_digest,),
            ).fetchone()

            if existing is not None:
                if (
                    existing["receipt_json"]
                    != receipt_json
                ):
                    raise RuntimeError(
                        "immutable receipt collision"
                    )

                return integrity_digest

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
                    str(receipt["predecessor_id"]),
                    str(receipt["successor_id"]),
                    receipt_json,
                ),
            )

        return integrity_digest

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
                (state_digest,),
            ).fetchone()

        if row is None:
            return None

        projection = json.loads(
            row["projection_json"]
        )

        state = _state_from_projection(
            projection
        )

        if state.state_digest != state_digest:
            raise RuntimeError(
                "stored state failed integrity check"
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
                (integrity_digest,),
            ).fetchone()

        if row is None:
            return None

        receipt = json.loads(
            row["receipt_json"]
        )

        body = dict(receipt)
        supplied = body.pop(
            "integrity_digest"
        )

        if supplied != _digest(body):
            raise RuntimeError(
                "stored receipt failed integrity check"
            )

        return receipt
