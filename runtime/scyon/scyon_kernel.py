#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

CONTRACT_PATH = (
    ROOT
    / "canon/structure/SAVANT_SCYON_FOCAL_CONTRACT_v1.0.0.json"
)

SCYON_TIERS = (
    "trait",
    "quirk",
    "prodigal",
    "exile",
    "innate",
    "portal",
    "obelisk",
)

ATOMIC_TIERS = (
    "iota",
    "mote",
)

TIER_RANK = {
    tier: rank
    for rank, tier in enumerate(
        SCYON_TIERS,
        start=1,
    )
}

EQUALIZER_CHANNELS = (
    "adaptivity",
    "automation",
    "authority_strictness",
    "causal_depth",
    "composition_depth",
    "confidence_threshold",
    "exploration",
    "metadata_influence",
    "projection_detail",
    "simulation_breadth",
    "temporal_depth",
    "validation_rigor",
)

AUTHORITY_STATES = (
    "observed",
    "proposed",
    "provisional",
    "accepted",
    "superseded",
    "rejected",
)


class ScyonError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(
    *values: Any,
) -> str:
    hasher = hashlib.sha256()

    for value in values:
        if isinstance(value, bytes):
            encoded = value

        elif isinstance(value, str):
            encoded = value.encode(
                "utf-8"
            )

        else:
            encoded = canonical_json(
                value
            ).encode(
                "utf-8"
            )

        hasher.update(
            len(encoded).to_bytes(
                8,
                "big",
            )
        )

        hasher.update(
            encoded
        )

    return hasher.hexdigest()


def parse_json(
    value: str,
) -> Any:
    try:
        return json.loads(
            value
        )

    except json.JSONDecodeError as exc:
        raise ScyonError(
            f"invalid JSON: {exc}"
        ) from exc


def load_contract() -> dict[str, Any]:
    if not CONTRACT_PATH.is_file():
        raise ScyonError(
            f"missing contract: {CONTRACT_PATH}"
        )

    contract = json.loads(
        CONTRACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if (
        contract.get(
            "contract_id"
        )
        != "savant.scyon-focal.contract"
    ):
        raise ScyonError(
            "invalid Scyon contract identity"
        )

    if (
        contract.get(
            "mutation_authorized"
        )
        is not False
    ):
        raise ScyonError(
            "mutation_authorized must remain false"
        )

    if (
        contract.get(
            "physical_migration_authorized"
        )
        is not False
    ):
        raise ScyonError(
            "physical_migration_authorized "
            "must remain false"
        )

    if (
        contract
        .get(
            "identity_tiers",
            {},
        )
        .get(
            "scyon_bearing"
        )
        != list(
            SCYON_TIERS
        )
    ):
        raise ScyonError(
            "Scyon tier contract mismatch"
        )

    return contract


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS focal (
    focal_id TEXT PRIMARY KEY,
    focal_kind TEXT NOT NULL,
    config_json TEXT NOT NULL,
    authority_state TEXT NOT NULL,
    digest TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scyon (
    scyon_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    owner_tier TEXT NOT NULL,
    archetype TEXT NOT NULL,
    focal_id TEXT REFERENCES focal(focal_id),
    authority_state TEXT NOT NULL,
    digest TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS equalizer (
    scyon_id TEXT NOT NULL
        REFERENCES scyon(scyon_id),
    channel TEXT NOT NULL,
    value REAL NOT NULL
        CHECK (
            value >= 0.0
            AND value <= 1.0
        ),
    authority_state TEXT NOT NULL,
    PRIMARY KEY (
        scyon_id,
        channel
    )
);

CREATE TABLE IF NOT EXISTS metadata (
    metadata_id TEXT PRIMARY KEY,
    scyon_id TEXT NOT NULL
        REFERENCES scyon(scyon_id),
    namespace TEXT NOT NULL,
    metadata_key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    authority_state TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    digest TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ability (
    ability_id TEXT PRIMARY KEY,
    scyon_id TEXT NOT NULL
        REFERENCES scyon(scyon_id),
    ability_name TEXT NOT NULL,
    minimum_tier TEXT NOT NULL,
    contract_json TEXT NOT NULL,
    authority_state TEXT NOT NULL,
    digest TEXT NOT NULL,
    UNIQUE (
        scyon_id,
        ability_name
    )
);

CREATE TABLE IF NOT EXISTS event (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    scyon_id TEXT NOT NULL
        REFERENCES scyon(scyon_id),
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    authority_json TEXT NOT NULL,
    lineage_json TEXT NOT NULL,
    graph_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    previous_digest TEXT,
    digest TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS event_no_update
BEFORE UPDATE ON event
BEGIN
    SELECT RAISE(
        ABORT,
        'Scyon events are immutable'
    );
END;

CREATE TRIGGER IF NOT EXISTS event_no_delete
BEFORE DELETE ON event
BEGIN
    SELECT RAISE(
        ABORT,
        'Scyon events are immutable'
    );
END;

CREATE TABLE IF NOT EXISTS branch (
    branch_id TEXT PRIMARY KEY,
    scyon_id TEXT NOT NULL
        REFERENCES scyon(scyon_id),
    label TEXT NOT NULL,
    assumptions_json TEXT NOT NULL,
    baseline_sequence INTEGER NOT NULL,
    digest TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scyon_composition (
    composition_id TEXT PRIMARY KEY,
    parent_scyon_id TEXT NOT NULL
        REFERENCES scyon(scyon_id),
    constituent_scyon_id TEXT NOT NULL
        REFERENCES scyon(scyon_id),
    relation TEXT NOT NULL,
    authority_state TEXT NOT NULL,
    lineage_json TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    digest TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (
        parent_scyon_id,
        constituent_scyon_id,
        relation
    ),
    CHECK (
        parent_scyon_id
        <> constituent_scyon_id
    )
);

CREATE INDEX IF NOT EXISTS
    idx_scyon_composition_parent
ON scyon_composition (
    parent_scyon_id
);

CREATE INDEX IF NOT EXISTS
    idx_scyon_composition_constituent
ON scyon_composition (
    constituent_scyon_id
);
"""


class ScyonKernel:
    def __init__(
        self,
        database_path: Path,
    ) -> None:
        self.contract = (
            load_contract()
        )

        if (
            not database_path.is_absolute()
        ):
            raise ScyonError(
                "database path must be absolute"
            )

        self.database_path = (
            database_path.resolve()
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.db = sqlite3.connect(
            self.database_path
        )

        self.db.row_factory = (
            sqlite3.Row
        )

        self.db.execute(
            "PRAGMA foreign_keys = ON"
        )

        self.db.execute(
            "PRAGMA journal_mode = WAL"
        )

        self.db.execute(
            "PRAGMA synchronous = FULL"
        )

        self.db.executescript(
            SCHEMA
        )

    def close(
        self,
    ) -> None:
        self.db.commit()
        self.db.close()

    def create_focal(
        self,
        focal_id: str,
        focal_kind: str,
        config: dict[str, Any],
        authority_state: str = "provisional",
    ) -> dict[str, Any]:
        self._require_authority(
            authority_state
        )

        focal_digest = digest(
            focal_id,
            focal_kind,
            config,
            authority_state,
        )

        self.db.execute(
            """
            INSERT INTO focal (
                focal_id,
                focal_kind,
                config_json,
                authority_state,
                digest,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                focal_id,
                focal_kind,
                canonical_json(
                    config
                ),
                authority_state,
                focal_digest,
                now(),
            ),
        )

        return {
            "focal_id": focal_id,
            "focal_kind": focal_kind,
            "digest": focal_digest,
        }

    def create_scyon(
        self,
        scyon_id: str,
        owner_id: str,
        owner_tier: str,
        archetype: str,
        focal_id: str | None = None,
        authority_state: str = "provisional",
    ) -> dict[str, Any]:
        if (
            owner_tier
            in ATOMIC_TIERS
            or owner_tier
            not in SCYON_TIERS
        ):
            raise ScyonError(
                f"{owner_tier} cannot own a Scyon"
            )

        self._require_authority(
            authority_state
        )

        if focal_id is not None:
            focal = self.db.execute(
                """
                SELECT focal_id
                FROM focal
                WHERE focal_id = ?
                """,
                (
                    focal_id,
                ),
            ).fetchone()

            if focal is None:
                raise ScyonError(
                    f"unknown Focal: {focal_id}"
                )

        scyon_digest = digest(
            scyon_id,
            owner_id,
            owner_tier,
            archetype,
            focal_id,
            authority_state,
        )

        self.db.execute(
            """
            INSERT INTO scyon (
                scyon_id,
                owner_id,
                owner_tier,
                archetype,
                focal_id,
                authority_state,
                digest,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scyon_id,
                owner_id,
                owner_tier,
                archetype,
                focal_id,
                authority_state,
                scyon_digest,
                now(),
            ),
        )

        for channel in (
            EQUALIZER_CHANNELS
        ):
            self.db.execute(
                """
                INSERT INTO equalizer (
                    scyon_id,
                    channel,
                    value,
                    authority_state
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    scyon_id,
                    channel,
                    0.5,
                    "provisional",
                ),
            )

        self.append_event(
            scyon_id=scyon_id,
            event_type="scyon.created",
            payload={
                "owner_id": owner_id,
                "owner_tier": owner_tier,
                "archetype": archetype,
                "focal_id": focal_id,
            },
            authority={
                "state": authority_state,
            },
            lineage={
                "created_by": (
                    "scyon_kernel"
                ),
                "depends_on": [],
            },
            graph={
                "source_node": scyon_id,
                "relation": (
                    "substantiates"
                ),
                "target_node": owner_id,
            },
            provenance={
                "contract": (
                    self.contract[
                        "contract_id"
                    ]
                ),
                "contract_version": (
                    self.contract[
                        "version"
                    ]
                ),
            },
        )

        return self.profile(
            scyon_id
        )

    def compose_scyon(
        self,
        parent_scyon_id: str,
        constituent_scyon_id: str,
        relation: str = "composes",
        authority_state: str = "provisional",
        lineage: dict[str, Any] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        parent = self._require_scyon(
            parent_scyon_id
        )

        constituent = (
            self._require_scyon(
                constituent_scyon_id
            )
        )

        self._require_authority(
            authority_state
        )

        if (
            parent_scyon_id
            == constituent_scyon_id
        ):
            raise ScyonError(
                "a Scyon cannot compose itself"
            )

        if (
            not isinstance(
                relation,
                str,
            )
            or not relation.strip()
        ):
            raise ScyonError(
                "composition relation "
                "must be non-empty"
            )

        parent_rank = (
            TIER_RANK[
                parent[
                    "owner_tier"
                ]
            ]
        )

        constituent_rank = (
            TIER_RANK[
                constituent[
                    "owner_tier"
                ]
            ]
        )

        if (
            constituent_rank
            >= parent_rank
        ):
            raise ScyonError(
                (
                    "constituent Scyon tier "
                    "must be lower than "
                    "parent Scyon tier: "
                    f"{constituent['owner_tier']} "
                    f"!< {parent['owner_tier']}"
                )
            )

        if self._reachable(
            start_scyon_id=(
                constituent_scyon_id
            ),
            target_scyon_id=(
                parent_scyon_id
            ),
        ):
            raise ScyonError(
                "composition would create a cycle"
            )

        normalized_relation = (
            relation.strip()
        )

        existing = self.db.execute(
            """
            SELECT composition_id
            FROM scyon_composition
            WHERE
                parent_scyon_id = ?
                AND constituent_scyon_id = ?
                AND relation = ?
            """,
            (
                parent_scyon_id,
                constituent_scyon_id,
                normalized_relation,
            ),
        ).fetchone()

        if existing is not None:
            raise ScyonError(
                (
                    "composition already exists: "
                    f"{existing['composition_id']}"
                )
            )

        composition_id = (
            "composition:"
            + uuid.uuid4().hex
        )

        lineage_value = (
            dict(lineage)
            if lineage is not None
            else {
                "created_by": (
                    "scyon_kernel"
                ),
                "parent": (
                    parent_scyon_id
                ),
                "constituent": (
                    constituent_scyon_id
                ),
            }
        )

        provenance_value = (
            dict(provenance)
            if provenance is not None
            else {
                "source": (
                    "scyon_kernel"
                ),
                "contract": (
                    self.contract[
                        "contract_id"
                    ]
                ),
                "contract_version": (
                    self.contract[
                        "version"
                    ]
                ),
            }
        )

        created_at = now()

        composition_digest = digest(
            composition_id,
            parent_scyon_id,
            constituent_scyon_id,
            normalized_relation,
            authority_state,
            lineage_value,
            provenance_value,
            created_at,
        )

        self.db.execute(
            """
            INSERT INTO scyon_composition (
                composition_id,
                parent_scyon_id,
                constituent_scyon_id,
                relation,
                authority_state,
                lineage_json,
                provenance_json,
                digest,
                created_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                composition_id,
                parent_scyon_id,
                constituent_scyon_id,
                normalized_relation,
                authority_state,
                canonical_json(
                    lineage_value
                ),
                canonical_json(
                    provenance_value
                ),
                composition_digest,
                created_at,
            ),
        )

        self.append_event(
            scyon_id=parent_scyon_id,
            event_type=(
                "scyon.composition.added"
            ),
            payload={
                "composition_id": (
                    composition_id
                ),
                "constituent_scyon_id": (
                    constituent_scyon_id
                ),
                "constituent_owner_id": (
                    constituent[
                        "owner_id"
                    ]
                ),
                "constituent_owner_tier": (
                    constituent[
                        "owner_tier"
                    ]
                ),
                "relation": (
                    normalized_relation
                ),
            },
            authority={
                "state": (
                    authority_state
                ),
            },
            lineage=(
                lineage_value
            ),
            graph={
                "source_node": (
                    parent_scyon_id
                ),
                "relation": (
                    normalized_relation
                ),
                "target_node": (
                    constituent_scyon_id
                ),
            },
            provenance=(
                provenance_value
            ),
        )

        return self._composition_record(
            composition_id
        )

    def constituents(
        self,
        scyon_id: str,
        recursive: bool = False,
    ) -> list[dict[str, Any]]:
        self._require_scyon(
            scyon_id
        )

        if not recursive:
            rows = self.db.execute(
                """
                SELECT
                    c.*,
                    s.owner_id,
                    s.owner_tier,
                    s.archetype,
                    s.focal_id
                FROM scyon_composition AS c
                JOIN scyon AS s
                  ON s.scyon_id
                     = c.constituent_scyon_id
                WHERE c.parent_scyon_id = ?
                ORDER BY
                    s.owner_tier,
                    c.constituent_scyon_id,
                    c.relation
                """,
                (
                    scyon_id,
                ),
            ).fetchall()

            return [
                self._composition_row_to_dict(
                    row,
                    depth=1,
                )
                for row in rows
            ]

        return self._recursive_constituents(
            scyon_id
        )

    def dependents(
        self,
        scyon_id: str,
    ) -> list[dict[str, Any]]:
        self._require_scyon(
            scyon_id
        )

        rows = self.db.execute(
            """
            SELECT
                c.*,
                s.owner_id,
                s.owner_tier,
                s.archetype,
                s.focal_id
            FROM scyon_composition AS c
            JOIN scyon AS s
              ON s.scyon_id
                 = c.parent_scyon_id
            WHERE c.constituent_scyon_id = ?
            ORDER BY
                s.owner_tier,
                c.parent_scyon_id,
                c.relation
            """,
            (
                scyon_id,
            ),
        ).fetchall()

        return [
            {
                "composition_id": (
                    row[
                        "composition_id"
                    ]
                ),
                "parent_scyon_id": (
                    row[
                        "parent_scyon_id"
                    ]
                ),
                "parent_owner_id": (
                    row[
                        "owner_id"
                    ]
                ),
                "parent_owner_tier": (
                    row[
                        "owner_tier"
                    ]
                ),
                "parent_archetype": (
                    row[
                        "archetype"
                    ]
                ),
                "parent_focal_id": (
                    row[
                        "focal_id"
                    ]
                ),
                "relation": (
                    row[
                        "relation"
                    ]
                ),
                "authority_state": (
                    row[
                        "authority_state"
                    ]
                ),
                "digest": (
                    row[
                        "digest"
                    ]
                ),
                "created_at": (
                    row[
                        "created_at"
                    ]
                ),
            }
            for row in rows
        ]

    def recursive_profile(
        self,
        scyon_id: str,
    ) -> dict[str, Any]:
        base = self.profile(
            scyon_id
        )

        closure = self.constituents(
            scyon_id,
            recursive=True,
        )

        included_scyons = {
            scyon_id,
            *[
                item[
                    "constituent_scyon_id"
                ]
                for item in closure
            ],
        }

        placeholders = ",".join(
            "?"
            for _ in included_scyons
        )

        ability_rows = (
            self.db.execute(
                f"""
                SELECT
                    scyon_id,
                    ability_name,
                    minimum_tier,
                    authority_state,
                    digest
                FROM ability
                WHERE scyon_id IN (
                    {placeholders}
                )
                ORDER BY
                    ability_name,
                    scyon_id
                """,
                tuple(
                    sorted(
                        included_scyons
                    )
                ),
            ).fetchall()
            if included_scyons
            else []
        )

        ability_sources: dict[
            str,
            list[dict[str, Any]],
        ] = {}

        for row in ability_rows:
            ability_sources.setdefault(
                row[
                    "ability_name"
                ],
                [],
            ).append(
                {
                    "scyon_id": (
                        row[
                            "scyon_id"
                        ]
                    ),
                    "minimum_tier": (
                        row[
                            "minimum_tier"
                        ]
                    ),
                    "authority_state": (
                        row[
                            "authority_state"
                        ]
                    ),
                    "digest": (
                        row[
                            "digest"
                        ]
                    ),
                }
            )

        tier_counts = {
            tier: 0
            for tier in SCYON_TIERS
        }

        tier_counts[
            base[
                "owner_tier"
            ]
        ] += 1

        for item in closure:
            tier_counts[
                item[
                    "constituent_owner_tier"
                ]
            ] += 1

        tier_counts = {
            tier: count
            for tier, count
            in tier_counts.items()
            if count
        }

        composition_projection = {
            "root_scyon_id": (
                scyon_id
            ),
            "constituent_count": (
                len(
                    closure
                )
            ),
            "maximum_depth": (
                max(
                    (
                        item[
                            "depth"
                        ]
                        for item
                        in closure
                    ),
                    default=0,
                )
            ),
            "tier_counts": (
                tier_counts
            ),
            "effective_ability_names": (
                sorted(
                    ability_sources
                )
            ),
            "ability_sources": (
                ability_sources
            ),
            "constituents": (
                closure
            ),
        }

        composition_projection[
            "projection_digest"
        ] = digest(
            composition_projection
        )

        return {
            **base,
            "recursive_composition": (
                composition_projection
            ),
            "authority_effect": "none",
            "projection": True,
        }

    def put_metadata(
        self,
        scyon_id: str,
        namespace: str,
        key: str,
        value: Any,
        authority_state: str = "observed",
    ) -> str:
        self._require_scyon(
            scyon_id
        )

        self._require_authority(
            authority_state
        )

        metadata_id = (
            "metadata:"
            + uuid.uuid4().hex
        )

        provenance = {
            "source": "scyon_kernel",
        }

        metadata_digest = digest(
            scyon_id,
            namespace,
            key,
            value,
            authority_state,
            provenance,
        )

        self.db.execute(
            """
            INSERT INTO metadata (
                metadata_id,
                scyon_id,
                namespace,
                metadata_key,
                value_json,
                authority_state,
                provenance_json,
                recorded_at,
                digest
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metadata_id,
                scyon_id,
                namespace,
                key,
                canonical_json(
                    value
                ),
                authority_state,
                canonical_json(
                    provenance
                ),
                now(),
                metadata_digest,
            ),
        )

        return metadata_id

    def set_equalizer(
        self,
        scyon_id: str,
        channel: str,
        value: float,
        authority_state: str = "provisional",
    ) -> None:
        self._require_scyon(
            scyon_id
        )

        self._require_authority(
            authority_state
        )

        if (
            channel
            not in EQUALIZER_CHANNELS
            or not 0.0
            <= value
            <= 1.0
        ):
            raise ScyonError(
                "invalid equalizer setting"
            )

        self.db.execute(
            """
            UPDATE equalizer
            SET
                value = ?,
                authority_state = ?
            WHERE
                scyon_id = ?
                AND channel = ?
            """,
            (
                value,
                authority_state,
                scyon_id,
                channel,
            ),
        )

    def register_ability(
        self,
        scyon_id: str,
        ability_name: str,
        minimum_tier: str,
        contract: dict[str, Any],
        authority_state: str = "provisional",
    ) -> str:
        scyon = self._require_scyon(
            scyon_id
        )

        self._require_authority(
            authority_state
        )

        if (
            minimum_tier
            not in SCYON_TIERS
            or TIER_RANK[
                scyon[
                    "owner_tier"
                ]
            ]
            < TIER_RANK[
                minimum_tier
            ]
        ):
            raise ScyonError(
                "ability exceeds tier capacity"
            )

        ability_id = (
            f"ability:{scyon_id}:"
            f"{ability_name}"
        )

        ability_digest = digest(
            scyon_id,
            ability_name,
            minimum_tier,
            contract,
            authority_state,
        )

        self.db.execute(
            """
            INSERT INTO ability (
                ability_id,
                scyon_id,
                ability_name,
                minimum_tier,
                contract_json,
                authority_state,
                digest
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ability_id,
                scyon_id,
                ability_name,
                minimum_tier,
                canonical_json(
                    contract
                ),
                authority_state,
                ability_digest,
            ),
        )

        return ability_id

    def append_event(
        self,
        scyon_id: str,
        event_type: str,
        payload: dict[str, Any],
        authority: dict[str, Any],
        lineage: dict[str, Any],
        graph: dict[str, Any],
        provenance: dict[str, Any],
    ) -> str:
        self._require_scyon(
            scyon_id
        )

        previous = self.db.execute(
            """
            SELECT digest
            FROM event
            WHERE scyon_id = ?
            ORDER BY sequence DESC
            LIMIT 1
            """,
            (
                scyon_id,
            ),
        ).fetchone()

        previous_digest = (
            previous[
                "digest"
            ]
            if previous
            else None
        )

        event_id = (
            "evt_"
            + uuid.uuid4().hex
        )

        recorded_at = now()

        event_digest = digest(
            event_id,
            scyon_id,
            event_type,
            payload,
            authority,
            lineage,
            graph,
            provenance,
            recorded_at,
            previous_digest,
        )

        self.db.execute(
            """
            INSERT INTO event (
                event_id,
                scyon_id,
                event_type,
                payload_json,
                authority_json,
                lineage_json,
                graph_json,
                provenance_json,
                recorded_at,
                previous_digest,
                digest
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                scyon_id,
                event_type,
                canonical_json(
                    payload
                ),
                canonical_json(
                    authority
                ),
                canonical_json(
                    lineage
                ),
                canonical_json(
                    graph
                ),
                canonical_json(
                    provenance
                ),
                recorded_at,
                previous_digest,
                event_digest,
            ),
        )

        return event_id

    def create_branch(
        self,
        scyon_id: str,
        label: str,
        assumptions: dict[str, Any],
    ) -> str:
        self._require_scyon(
            scyon_id
        )

        baseline = self.db.execute(
            """
            SELECT COALESCE(
                MAX(sequence),
                0
            )
            FROM event
            WHERE scyon_id = ?
            """,
            (
                scyon_id,
            ),
        ).fetchone()[0]

        branch_id = (
            "branch:"
            + uuid.uuid4().hex
        )

        branch_digest = digest(
            branch_id,
            scyon_id,
            label,
            assumptions,
            baseline,
        )

        self.db.execute(
            """
            INSERT INTO branch (
                branch_id,
                scyon_id,
                label,
                assumptions_json,
                baseline_sequence,
                digest,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                branch_id,
                scyon_id,
                label,
                canonical_json(
                    assumptions
                ),
                baseline,
                branch_digest,
                now(),
            ),
        )

        return branch_id

    def profile(
        self,
        scyon_id: str,
    ) -> dict[str, Any]:
        row = self._require_scyon(
            scyon_id
        )

        equalizer = self.db.execute(
            """
            SELECT
                channel,
                value,
                authority_state
            FROM equalizer
            WHERE scyon_id = ?
            ORDER BY channel
            """,
            (
                scyon_id,
            ),
        ).fetchall()

        direct_constituents = (
            self.constituents(
                scyon_id,
                recursive=False,
            )
        )

        direct_dependents = (
            self.dependents(
                scyon_id
            )
        )

        return {
            "scyon_id": (
                row[
                    "scyon_id"
                ]
            ),
            "owner_id": (
                row[
                    "owner_id"
                ]
            ),
            "owner_tier": (
                row[
                    "owner_tier"
                ]
            ),
            "tier_rank": (
                TIER_RANK[
                    row[
                        "owner_tier"
                    ]
                ]
            ),
            "archetype": (
                row[
                    "archetype"
                ]
            ),
            "focal_id": (
                row[
                    "focal_id"
                ]
            ),
            "authority_state": (
                row[
                    "authority_state"
                ]
            ),
            "digest": (
                row[
                    "digest"
                ]
            ),
            "equalizer": {
                item[
                    "channel"
                ]: {
                    "value": (
                        item[
                            "value"
                        ]
                    ),
                    "authority_state": (
                        item[
                            "authority_state"
                        ]
                    ),
                }
                for item in equalizer
            },
            "composition": {
                "direct_constituents": (
                    direct_constituents
                ),
                "direct_constituent_count": (
                    len(
                        direct_constituents
                    )
                ),
                "direct_dependents": (
                    direct_dependents
                ),
                "direct_dependent_count": (
                    len(
                        direct_dependents
                    )
                ),
            },
        }

    def validate(
        self,
    ) -> dict[str, Any]:
        integrity = self.db.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        foreign_keys = self.db.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        chain_errors: list[
            str
        ] = []

        for scyon in self.db.execute(
            """
            SELECT scyon_id
            FROM scyon
            ORDER BY scyon_id
            """
        ):
            previous_digest = None

            for event in self.db.execute(
                """
                SELECT *
                FROM event
                WHERE scyon_id = ?
                ORDER BY sequence
                """,
                (
                    scyon[
                        "scyon_id"
                    ],
                ),
            ):
                if (
                    event[
                        "previous_digest"
                    ]
                    != previous_digest
                ):
                    chain_errors.append(
                        event[
                            "event_id"
                        ]
                        + (
                            ": previous "
                            "digest mismatch"
                        )
                    )

                calculated = digest(
                    event[
                        "event_id"
                    ],
                    event[
                        "scyon_id"
                    ],
                    event[
                        "event_type"
                    ],
                    json.loads(
                        event[
                            "payload_json"
                        ]
                    ),
                    json.loads(
                        event[
                            "authority_json"
                        ]
                    ),
                    json.loads(
                        event[
                            "lineage_json"
                        ]
                    ),
                    json.loads(
                        event[
                            "graph_json"
                        ]
                    ),
                    json.loads(
                        event[
                            "provenance_json"
                        ]
                    ),
                    event[
                        "recorded_at"
                    ],
                    event[
                        "previous_digest"
                    ],
                )

                if (
                    calculated
                    != event[
                        "digest"
                    ]
                ):
                    chain_errors.append(
                        event[
                            "event_id"
                        ]
                        + ": digest mismatch"
                    )

                previous_digest = (
                    event[
                        "digest"
                    ]
                )

        composition_errors = (
            self._validate_composition()
        )

        valid = (
            integrity == "ok"
            and not foreign_keys
            and not chain_errors
            and not composition_errors
        )

        return {
            "database": str(
                self.database_path
            ),
            "integrity": (
                integrity
            ),
            "foreign_key_errors": (
                len(
                    foreign_keys
                )
            ),
            "event_chain_errors": (
                chain_errors
            ),
            "composition_errors": (
                composition_errors
            ),
            "composition_edge_count": (
                self.db.execute(
                    """
                    SELECT COUNT(*)
                    FROM scyon_composition
                    """
                ).fetchone()[0]
            ),
            "recursive_composition": True,
            "kernel_substantiated_once": True,
            "mutation_authorized": False,
            "physical_migration_authorized": (
                False
            ),
            "valid": valid,
        }

    def _validate_composition(
        self,
    ) -> list[str]:
        errors: list[
            str
        ] = []

        rows = self.db.execute(
            """
            SELECT
                c.*,
                parent.owner_tier
                    AS parent_tier,
                child.owner_tier
                    AS constituent_tier
            FROM scyon_composition AS c
            JOIN scyon AS parent
              ON parent.scyon_id
                 = c.parent_scyon_id
            JOIN scyon AS child
              ON child.scyon_id
                 = c.constituent_scyon_id
            ORDER BY c.composition_id
            """
        ).fetchall()

        for row in rows:
            if (
                row[
                    "parent_scyon_id"
                ]
                == row[
                    "constituent_scyon_id"
                ]
            ):
                errors.append(
                    (
                        row[
                            "composition_id"
                        ]
                        + ": self composition"
                    )
                )

            if (
                TIER_RANK[
                    row[
                        "constituent_tier"
                    ]
                ]
                >= TIER_RANK[
                    row[
                        "parent_tier"
                    ]
                ]
            ):
                errors.append(
                    (
                        row[
                            "composition_id"
                        ]
                        + ": invalid tier direction"
                    )
                )

            calculated = digest(
                row[
                    "composition_id"
                ],
                row[
                    "parent_scyon_id"
                ],
                row[
                    "constituent_scyon_id"
                ],
                row[
                    "relation"
                ],
                row[
                    "authority_state"
                ],
                json.loads(
                    row[
                        "lineage_json"
                    ]
                ),
                json.loads(
                    row[
                        "provenance_json"
                    ]
                ),
                row[
                    "created_at"
                ],
            )

            if (
                calculated
                != row[
                    "digest"
                ]
            ):
                errors.append(
                    (
                        row[
                            "composition_id"
                        ]
                        + ": digest mismatch"
                    )
                )

        for scyon in self.db.execute(
            """
            SELECT scyon_id
            FROM scyon
            ORDER BY scyon_id
            """
        ):
            if self._has_cycle_from(
                scyon[
                    "scyon_id"
                ]
            ):
                errors.append(
                    (
                        scyon[
                            "scyon_id"
                        ]
                        + (
                            ": composition "
                            "cycle detected"
                        )
                    )
                )

        return sorted(
            set(
                errors
            )
        )

    def _has_cycle_from(
        self,
        scyon_id: str,
    ) -> bool:
        visited: set[
            str
        ] = set()

        active: set[
            str
        ] = set()

        def visit(
            current: str,
        ) -> bool:
            if current in active:
                return True

            if current in visited:
                return False

            visited.add(
                current
            )

            active.add(
                current
            )

            children = self.db.execute(
                """
                SELECT constituent_scyon_id
                FROM scyon_composition
                WHERE parent_scyon_id = ?
                ORDER BY constituent_scyon_id
                """,
                (
                    current,
                ),
            ).fetchall()

            for child in children:
                if visit(
                    child[
                        "constituent_scyon_id"
                    ]
                ):
                    return True

            active.remove(
                current
            )

            return False

        return visit(
            scyon_id
        )

    def _reachable(
        self,
        start_scyon_id: str,
        target_scyon_id: str,
    ) -> bool:
        if (
            start_scyon_id
            == target_scyon_id
        ):
            return True

        visited: set[
            str
        ] = set()

        pending = [
            start_scyon_id
        ]

        while pending:
            current = pending.pop()

            if current in visited:
                continue

            visited.add(
                current
            )

            rows = self.db.execute(
                """
                SELECT constituent_scyon_id
                FROM scyon_composition
                WHERE parent_scyon_id = ?
                ORDER BY constituent_scyon_id
                """,
                (
                    current,
                ),
            ).fetchall()

            for row in rows:
                child = row[
                    "constituent_scyon_id"
                ]

                if (
                    child
                    == target_scyon_id
                ):
                    return True

                if child not in visited:
                    pending.append(
                        child
                    )

        return False

    def _recursive_constituents(
        self,
        root_scyon_id: str,
    ) -> list[dict[str, Any]]:
        result: list[
            dict[str, Any]
        ] = []

        visited_edges: set[
            str
        ] = set()

        def walk(
            parent_scyon_id: str,
            depth: int,
        ) -> None:
            rows = self.db.execute(
                """
                SELECT
                    c.*,
                    s.owner_id,
                    s.owner_tier,
                    s.archetype,
                    s.focal_id
                FROM scyon_composition AS c
                JOIN scyon AS s
                  ON s.scyon_id
                     = c.constituent_scyon_id
                WHERE c.parent_scyon_id = ?
                ORDER BY
                    s.owner_tier,
                    c.constituent_scyon_id,
                    c.relation
                """,
                (
                    parent_scyon_id,
                ),
            ).fetchall()

            for row in rows:
                composition_id = (
                    row[
                        "composition_id"
                    ]
                )

                if (
                    composition_id
                    in visited_edges
                ):
                    continue

                visited_edges.add(
                    composition_id
                )

                result.append(
                    self._composition_row_to_dict(
                        row,
                        depth=depth,
                    )
                )

                walk(
                    row[
                        "constituent_scyon_id"
                    ],
                    depth + 1,
                )

        walk(
            root_scyon_id,
            1,
        )

        result.sort(
            key=lambda item: (
                item[
                    "depth"
                ],
                item[
                    "constituent_scyon_id"
                ],
                item[
                    "relation"
                ],
            )
        )

        return result

    def _composition_row_to_dict(
        self,
        row: sqlite3.Row,
        depth: int,
    ) -> dict[str, Any]:
        return {
            "composition_id": (
                row[
                    "composition_id"
                ]
            ),
            "parent_scyon_id": (
                row[
                    "parent_scyon_id"
                ]
            ),
            "constituent_scyon_id": (
                row[
                    "constituent_scyon_id"
                ]
            ),
            "constituent_owner_id": (
                row[
                    "owner_id"
                ]
            ),
            "constituent_owner_tier": (
                row[
                    "owner_tier"
                ]
            ),
            "constituent_archetype": (
                row[
                    "archetype"
                ]
            ),
            "constituent_focal_id": (
                row[
                    "focal_id"
                ]
            ),
            "relation": (
                row[
                    "relation"
                ]
            ),
            "authority_state": (
                row[
                    "authority_state"
                ]
            ),
            "lineage": json.loads(
                row[
                    "lineage_json"
                ]
            ),
            "provenance": json.loads(
                row[
                    "provenance_json"
                ]
            ),
            "digest": (
                row[
                    "digest"
                ]
            ),
            "created_at": (
                row[
                    "created_at"
                ]
            ),
            "depth": depth,
        }

    def _composition_record(
        self,
        composition_id: str,
    ) -> dict[str, Any]:
        row = self.db.execute(
            """
            SELECT
                c.*,
                s.owner_id,
                s.owner_tier,
                s.archetype,
                s.focal_id
            FROM scyon_composition AS c
            JOIN scyon AS s
              ON s.scyon_id
                 = c.constituent_scyon_id
            WHERE c.composition_id = ?
            """,
            (
                composition_id,
            ),
        ).fetchone()

        if row is None:
            raise ScyonError(
                (
                    "unknown composition: "
                    f"{composition_id}"
                )
            )

        return self._composition_row_to_dict(
            row,
            depth=1,
        )

    def _require_scyon(
        self,
        scyon_id: str,
    ) -> sqlite3.Row:
        row = self.db.execute(
            """
            SELECT *
            FROM scyon
            WHERE scyon_id = ?
            """,
            (
                scyon_id,
            ),
        ).fetchone()

        if row is None:
            raise ScyonError(
                f"unknown Scyon: {scyon_id}"
            )

        return row

    @staticmethod
    def _require_authority(
        authority_state: str,
    ) -> None:
        if (
            authority_state
            not in AUTHORITY_STATES
        ):
            raise ScyonError(
                (
                    "invalid authority state: "
                    f"{authority_state}"
                )
            )


def self_test() -> int:
    with tempfile.TemporaryDirectory() as temp:
        kernel = ScyonKernel(
            Path(temp).resolve()
            / "scyon.sqlite3"
        )

        try:
            kernel.create_focal(
                focal_id=(
                    "focal:simulation"
                ),
                focal_kind=(
                    "simulation"
                ),
                config={
                    "branch_safe": True,
                    "counterfactual": True,
                    "canonical_mutation": False,
                },
                authority_state="accepted",
            )

            kernel.create_focal(
                focal_id=(
                    "focal:test-trait"
                ),
                focal_kind=(
                    "test-trait"
                ),
                config={},
                authority_state="accepted",
            )

            kernel.create_focal(
                focal_id=(
                    "focal:test-quirk"
                ),
                focal_kind=(
                    "test-quirk"
                ),
                config={},
                authority_state="accepted",
            )

            kernel.create_focal(
                focal_id=(
                    "focal:test-prodigal"
                ),
                focal_kind=(
                    "test-prodigal"
                ),
                config={},
                authority_state="accepted",
            )

            kernel.create_scyon(
                scyon_id=(
                    "scyon:trait:test"
                ),
                owner_id=(
                    "trait:test"
                ),
                owner_tier=(
                    "trait"
                ),
                archetype=(
                    "test-trait"
                ),
                focal_id=(
                    "focal:test-trait"
                ),
                authority_state="accepted",
            )

            kernel.create_scyon(
                scyon_id=(
                    "scyon:quirk:test"
                ),
                owner_id=(
                    "quirk:test"
                ),
                owner_tier=(
                    "quirk"
                ),
                archetype=(
                    "test-quirk"
                ),
                focal_id=(
                    "focal:test-quirk"
                ),
                authority_state="accepted",
            )

            kernel.create_scyon(
                scyon_id=(
                    "scyon:prodigal:test"
                ),
                owner_id=(
                    "prodigal:test"
                ),
                owner_tier=(
                    "prodigal"
                ),
                archetype=(
                    "test-prodigal"
                ),
                focal_id=(
                    "focal:test-prodigal"
                ),
                authority_state="accepted",
            )

            kernel.create_scyon(
                scyon_id=(
                    "scyon:exile:simulation"
                ),
                owner_id=(
                    "exile:simulation"
                ),
                owner_tier=(
                    "exile"
                ),
                archetype=(
                    "simulation-jurisdiction"
                ),
                focal_id=(
                    "focal:simulation"
                ),
                authority_state="accepted",
            )

            kernel.register_ability(
                scyon_id=(
                    "scyon:trait:test"
                ),
                ability_name=(
                    "atomic-observation"
                ),
                minimum_tier="trait",
                contract={
                    "authoritative": False,
                },
                authority_state="accepted",
            )

            kernel.register_ability(
                scyon_id=(
                    "scyon:quirk:test"
                ),
                ability_name=(
                    "conditional-pattern"
                ),
                minimum_tier="quirk",
                contract={
                    "authoritative": False,
                },
                authority_state="accepted",
            )

            kernel.register_ability(
                scyon_id=(
                    "scyon:prodigal:test"
                ),
                ability_name=(
                    "autonomous-capability"
                ),
                minimum_tier="prodigal",
                contract={
                    "authoritative": False,
                },
                authority_state="accepted",
            )

            kernel.register_ability(
                scyon_id=(
                    "scyon:exile:simulation"
                ),
                ability_name=(
                    "counterfactual-analysis"
                ),
                minimum_tier="exile",
                contract={
                    "branch_safe": True,
                    "authoritative": False,
                },
                authority_state="accepted",
            )

            kernel.compose_scyon(
                parent_scyon_id=(
                    "scyon:quirk:test"
                ),
                constituent_scyon_id=(
                    "scyon:trait:test"
                ),
                authority_state="accepted",
            )

            kernel.compose_scyon(
                parent_scyon_id=(
                    "scyon:prodigal:test"
                ),
                constituent_scyon_id=(
                    "scyon:quirk:test"
                ),
                authority_state="accepted",
            )

            kernel.compose_scyon(
                parent_scyon_id=(
                    "scyon:exile:simulation"
                ),
                constituent_scyon_id=(
                    "scyon:prodigal:test"
                ),
                authority_state="accepted",
            )

            kernel.put_metadata(
                scyon_id=(
                    "scyon:exile:simulation"
                ),
                namespace="scenario",
                key="weather",
                value={
                    "condition": "rain"
                },
            )

            kernel.set_equalizer(
                scyon_id=(
                    "scyon:exile:simulation"
                ),
                channel=(
                    "simulation_breadth"
                ),
                value=1.0,
                authority_state="accepted",
            )

            branch_id = (
                kernel.create_branch(
                    scyon_id=(
                        "scyon:exile:simulation"
                    ),
                    label=(
                        "weather-counterfactual"
                    ),
                    assumptions={
                        "weather": "snow"
                    },
                )
            )

            recursive = (
                kernel.recursive_profile(
                    "scyon:exile:simulation"
                )
            )

            expected_abilities = {
                "atomic-observation",
                "conditional-pattern",
                "autonomous-capability",
                "counterfactual-analysis",
            }

            actual_abilities = set(
                recursive[
                    "recursive_composition"
                ][
                    "effective_ability_names"
                ]
            )

            if (
                actual_abilities
                != expected_abilities
            ):
                raise ScyonError(
                    (
                        "recursive ability "
                        "projection failed"
                    )
                )

            if (
                recursive[
                    "recursive_composition"
                ][
                    "constituent_count"
                ]
                != 3
            ):
                raise ScyonError(
                    (
                        "recursive constituent "
                        "closure failed"
                    )
                )

            if (
                recursive[
                    "recursive_composition"
                ][
                    "maximum_depth"
                ]
                != 3
            ):
                raise ScyonError(
                    (
                        "recursive composition "
                        "depth failed"
                    )
                )

            try:
                kernel.compose_scyon(
                    parent_scyon_id=(
                        "scyon:trait:test"
                    ),
                    constituent_scyon_id=(
                        "scyon:quirk:test"
                    ),
                    authority_state="accepted",
                )

            except ScyonError:
                pass

            else:
                raise ScyonError(
                    (
                        "invalid upward "
                        "composition accepted"
                    )
                )

            try:
                kernel.compose_scyon(
                    parent_scyon_id=(
                        "scyon:exile:simulation"
                    ),
                    constituent_scyon_id=(
                        "scyon:exile:simulation"
                    ),
                    authority_state="accepted",
                )

            except ScyonError:
                pass

            else:
                raise ScyonError(
                    (
                        "self composition "
                        "was accepted"
                    )
                )

            validation = (
                kernel.validate()
            )

            if not validation[
                "valid"
            ]:
                raise ScyonError(
                    (
                        "self-test "
                        "validation failed"
                    )
                )

            print(
                json.dumps(
                    {
                        "self_test": "passed",
                        "scyon": (
                            "scyon:exile:simulation"
                        ),
                        "focal": (
                            "focal:simulation"
                        ),
                        "branch": (
                            branch_id
                        ),
                        "recursive_composition": {
                            "constituent_count": (
                                recursive[
                                    "recursive_composition"
                                ][
                                    "constituent_count"
                                ]
                            ),
                            "maximum_depth": (
                                recursive[
                                    "recursive_composition"
                                ][
                                    "maximum_depth"
                                ]
                            ),
                            "effective_ability_names": (
                                recursive[
                                    "recursive_composition"
                                ][
                                    "effective_ability_names"
                                ]
                            ),
                        },
                        "validation": (
                            validation
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )

            return 0

        finally:
            kernel.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Savant Scyon kernel successor"
        )
    )

    parser.add_argument(
        "--database"
    )

    commands = (
        parser.add_subparsers(
            dest="command",
            required=True,
        )
    )

    commands.add_parser(
        "self-test"
    )

    focal = commands.add_parser(
        "create-focal"
    )

    focal.add_argument(
        "--focal-id",
        required=True,
    )

    focal.add_argument(
        "--focal-kind",
        required=True,
    )

    focal.add_argument(
        "--config-json",
        default="{}",
    )

    scyon = commands.add_parser(
        "create-scyon"
    )

    scyon.add_argument(
        "--scyon-id",
        required=True,
    )

    scyon.add_argument(
        "--owner-id",
        required=True,
    )

    scyon.add_argument(
        "--owner-tier",
        choices=SCYON_TIERS,
        required=True,
    )

    scyon.add_argument(
        "--archetype",
        required=True,
    )

    scyon.add_argument(
        "--focal-id"
    )

    composition = (
        commands.add_parser(
            "compose-scyon"
        )
    )

    composition.add_argument(
        "--parent-scyon-id",
        required=True,
    )

    composition.add_argument(
        "--constituent-scyon-id",
        required=True,
    )

    composition.add_argument(
        "--relation",
        default="composes",
    )

    constituents = (
        commands.add_parser(
            "constituents"
        )
    )

    constituents.add_argument(
        "--scyon-id",
        required=True,
    )

    constituents.add_argument(
        "--recursive",
        action="store_true",
    )

    dependents = commands.add_parser(
        "dependents"
    )

    dependents.add_argument(
        "--scyon-id",
        required=True,
    )

    profile = commands.add_parser(
        "profile"
    )

    profile.add_argument(
        "--scyon-id",
        required=True,
    )

    recursive_profile = (
        commands.add_parser(
            "recursive-profile"
        )
    )

    recursive_profile.add_argument(
        "--scyon-id",
        required=True,
    )

    commands.add_parser(
        "validate"
    )

    return parser


def main() -> int:
    arguments = (
        build_parser().parse_args()
    )

    if (
        arguments.command
        == "self-test"
    ):
        return self_test()

    if not arguments.database:
        raise ScyonError(
            "--database is required"
        )

    database_path = Path(
        arguments.database
    )

    if (
        not database_path.is_absolute()
    ):
        raise ScyonError(
            "--database must be absolute"
        )

    kernel = ScyonKernel(
        database_path
    )

    try:
        if (
            arguments.command
            == "create-focal"
        ):
            result = kernel.create_focal(
                focal_id=(
                    arguments.focal_id
                ),
                focal_kind=(
                    arguments.focal_kind
                ),
                config=parse_json(
                    arguments.config_json
                ),
            )

        elif (
            arguments.command
            == "create-scyon"
        ):
            result = kernel.create_scyon(
                scyon_id=(
                    arguments.scyon_id
                ),
                owner_id=(
                    arguments.owner_id
                ),
                owner_tier=(
                    arguments.owner_tier
                ),
                archetype=(
                    arguments.archetype
                ),
                focal_id=(
                    arguments.focal_id
                ),
            )

        elif (
            arguments.command
            == "compose-scyon"
        ):
            result = (
                kernel.compose_scyon(
                    parent_scyon_id=(
                        arguments.parent_scyon_id
                    ),
                    constituent_scyon_id=(
                        arguments.constituent_scyon_id
                    ),
                    relation=(
                        arguments.relation
                    ),
                )
            )

        elif (
            arguments.command
            == "constituents"
        ):
            result = {
                "scyon_id": (
                    arguments.scyon_id
                ),
                "recursive": (
                    arguments.recursive
                ),
                "constituents": (
                    kernel.constituents(
                        arguments.scyon_id,
                        recursive=(
                            arguments.recursive
                        ),
                    )
                ),
            }

        elif (
            arguments.command
            == "dependents"
        ):
            result = {
                "scyon_id": (
                    arguments.scyon_id
                ),
                "dependents": (
                    kernel.dependents(
                        arguments.scyon_id
                    )
                ),
            }

        elif (
            arguments.command
            == "profile"
        ):
            result = kernel.profile(
                arguments.scyon_id
            )

        elif (
            arguments.command
            == "recursive-profile"
        ):
            result = (
                kernel.recursive_profile(
                    arguments.scyon_id
                )
            )

        elif (
            arguments.command
            == "validate"
        ):
            result = kernel.validate()

            print(
                json.dumps(
                    result,
                    indent=2,
                    sort_keys=True,
                )
            )

            return (
                0
                if result[
                    "valid"
                ]
                else 1
            )

        else:
            raise ScyonError(
                "unsupported command"
            )

        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    finally:
        kernel.close()


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except (
        OSError,
        ScyonError,
        sqlite3.Error,
        json.JSONDecodeError,
    ) as exc:
        print(
            (
                "ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        raise SystemExit(1)
