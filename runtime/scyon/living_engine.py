#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator


DEFAULT_ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

DEFAULT_KERNEL = (
    DEFAULT_ROOT
    / "runtime/scyon/scyon_kernel.py"
)


class LivingEngineError(RuntimeError):
    pass


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
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise LivingEngineError(
            f"JSON root must be an object: {path}"
        )

    return value


def atomic_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(
            handle.fileno()
        )

        temporary = Path(
            handle.name
        )

    os.replace(
        temporary,
        path,
    )


def load_kernel(
    path: Path = DEFAULT_KERNEL,
) -> ModuleType:
    if not path.is_file():
        raise LivingEngineError(
            f"Scyon kernel unavailable: {path}"
        )

    specification = (
        importlib.util.spec_from_file_location(
            "savant_scyon_kernel",
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise LivingEngineError(
            f"cannot load Scyon kernel: {path}"
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    specification.loader.exec_module(
        module
    )

    return module


@dataclass(
    frozen=True,
    slots=True,
)
class LivingFocal:
    schema: str
    engine_id: str
    focal_id: str
    focal_kind: str
    scyon_id: str
    owner_id: str
    owner_tier: str
    archetype: str
    authority_state: str
    abilities: tuple[
        dict[str, Any],
        ...,
    ]
    equalizer: dict[
        str,
        float,
    ]
    metadata: dict[
        str,
        Any,
    ]
    policy: dict[
        str,
        Any,
    ]
    integrations: dict[
        str,
        Any,
    ]
    enhancements: tuple[
        str,
        ...,
    ]

    @classmethod
    def from_path(
        cls,
        path: Path,
    ) -> "LivingFocal":
        raw = load_json(
            path
        )

        required = (
            "schema",
            "engine_id",
            "focal_id",
            "focal_kind",
            "scyon_id",
            "owner_id",
            "owner_tier",
            "archetype",
            "authority_state",
            "abilities",
            "equalizer",
            "metadata",
            "policy",
            "integrations",
            "enhancements",
        )

        missing = [
            name
            for name in required
            if name not in raw
        ]

        if missing:
            raise LivingEngineError(
                "Focal missing fields: "
                + ", ".join(
                    missing
                )
            )

        if not isinstance(
            raw["abilities"],
            list,
        ):
            raise LivingEngineError(
                "abilities must be a list"
            )

        if not isinstance(
            raw["equalizer"],
            dict,
        ):
            raise LivingEngineError(
                "equalizer must be an object"
            )

        if not isinstance(
            raw["metadata"],
            dict,
        ):
            raise LivingEngineError(
                "metadata must be an object"
            )

        if not isinstance(
            raw["policy"],
            dict,
        ):
            raise LivingEngineError(
                "policy must be an object"
            )

        if not isinstance(
            raw["integrations"],
            dict,
        ):
            raise LivingEngineError(
                "integrations must be an object"
            )

        if (
            not isinstance(
                raw["enhancements"],
                list,
            )
            or len(
                raw["enhancements"]
            )
            < 20
        ):
            raise LivingEngineError(
                "enhancements must contain "
                "at least 20 entries"
            )

        return cls(
            schema=str(
                raw["schema"]
            ),
            engine_id=str(
                raw["engine_id"]
            ),
            focal_id=str(
                raw["focal_id"]
            ),
            focal_kind=str(
                raw["focal_kind"]
            ),
            scyon_id=str(
                raw["scyon_id"]
            ),
            owner_id=str(
                raw["owner_id"]
            ),
            owner_tier=str(
                raw["owner_tier"]
            ),
            archetype=str(
                raw["archetype"]
            ),
            authority_state=str(
                raw[
                    "authority_state"
                ]
            ),
            abilities=tuple(
                dict(item)
                for item
                in raw["abilities"]
            ),
            equalizer={
                str(key): float(value)
                for key, value
                in raw[
                    "equalizer"
                ].items()
            },
            metadata=dict(
                raw["metadata"]
            ),
            policy=dict(
                raw["policy"]
            ),
            integrations=dict(
                raw["integrations"]
            ),
            enhancements=tuple(
                str(item)
                for item
                in raw[
                    "enhancements"
                ]
            ),
        )

    def focal_config(
        self,
    ) -> dict[str, Any]:
        return {
            "engine_id": (
                self.engine_id
            ),
            "policy": (
                self.policy
            ),
            "integrations": (
                self.integrations
            ),
            "enhancements": list(
                self.enhancements
            ),
            "living_template_version": (
                "1.0.0"
            ),
        }


class LivingEngine:
    """
    Purpose-neutral living Scyon runtime.

    Canonical Scyon substance remains owned by
    ScyonKernel.

    This layer supplies reusable living behavior:
    lifecycle,
    idempotent specialization,
    observation,
    drift linkage,
    checkpoints,
    projections,
    concurrency protection,
    health validation,
    lineage,
    and provenance.

    A concrete living engine therefore becomes:

        Scyon kernel
        + LivingEngine
        + Focal
        + Focal metadata
        + Focal ability bindings

    No concrete living engine needs to copy the
    Scyon implementation.
    """

    def __init__(
        self,
        focal: LivingFocal,
        database: Path,
        *,
        root: Path = DEFAULT_ROOT,
        kernel_path: Path | None = None,
    ) -> None:
        if not database.is_absolute():
            raise LivingEngineError(
                "database path must be absolute"
            )

        self.root = (
            root.resolve()
        )

        self.focal = focal

        self.database = (
            database.resolve()
        )

        self.kernel_module = (
            load_kernel(
                kernel_path
                or (
                    self.root
                    / "runtime/scyon/"
                    "scyon_kernel.py"
                )
            )
        )

        self.kernel = (
            self.kernel_module.ScyonKernel(
                self.database
            )
        )

        self.lock_path = (
            self.database.with_suffix(
                self.database.suffix
                + ".lock"
            )
        )

    def close(
        self,
    ) -> None:
        self.kernel.close()

    def __enter__(
        self,
    ) -> "LivingEngine":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc: Any,
        tb: Any,
    ) -> None:
        self.close()

    @contextlib.contextmanager
    def locked(
        self,
    ) -> Iterator[None]:
        self.lock_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.lock_path.open(
            "a+",
            encoding="utf-8",
        ) as handle:
            fcntl.flock(
                handle.fileno(),
                fcntl.LOCK_EX,
            )

            try:
                yield

            finally:
                fcntl.flock(
                    handle.fileno(),
                    fcntl.LOCK_UN,
                )

    def _exists(
        self,
        table: str,
        column: str,
        value: str,
    ) -> bool:
        row = self.kernel.db.execute(
            (
                f"SELECT 1 "
                f"FROM {table} "
                f"WHERE {column} = ? "
                f"LIMIT 1"
            ),
            (
                value,
            ),
        ).fetchone()

        return (
            row is not None
        )

    def bootstrap(
        self,
    ) -> dict[str, Any]:
        with (
            self.locked(),
            self.kernel.db,
        ):
            if not self._exists(
                "focal",
                "focal_id",
                self.focal.focal_id,
            ):
                self.kernel.create_focal(
                    self.focal.focal_id,
                    self.focal.focal_kind,
                    self.focal.focal_config(),
                    self.focal.authority_state,
                )

            if not self._exists(
                "scyon",
                "scyon_id",
                self.focal.scyon_id,
            ):
                self.kernel.create_scyon(
                    self.focal.scyon_id,
                    self.focal.owner_id,
                    self.focal.owner_tier,
                    self.focal.archetype,
                    self.focal.focal_id,
                    self.focal.authority_state,
                )

            for ability in (
                self.focal.abilities
            ):
                name = str(
                    ability["name"]
                )

                ability_id = (
                    "ability:"
                    f"{self.focal.scyon_id}:"
                    f"{name}"
                )

                if not self._exists(
                    "ability",
                    "ability_id",
                    ability_id,
                ):
                    self.kernel.register_ability(
                        self.focal.scyon_id,
                        name,
                        str(
                            ability.get(
                                "minimum_tier",
                                self.focal.owner_tier,
                            )
                        ),
                        dict(
                            ability.get(
                                "contract",
                                {},
                            )
                        ),
                        str(
                            ability.get(
                                "authority_state",
                                self.focal.authority_state,
                            )
                        ),
                    )

            for (
                channel,
                value,
            ) in (
                self.focal.equalizer.items()
            ):
                self.kernel.set_equalizer(
                    self.focal.scyon_id,
                    channel,
                    value,
                    self.focal.authority_state,
                )

            existing = (
                self.kernel.db.execute(
                    """
                    SELECT COUNT(*)
                    FROM metadata
                    WHERE
                        scyon_id = ?
                        AND namespace = ?
                    """,
                    (
                        self.focal.scyon_id,
                        "living.focal",
                    ),
                ).fetchone()[0]
            )

            if not existing:
                for (
                    key,
                    value,
                ) in sorted(
                    self.focal.metadata.items()
                ):
                    self.kernel.put_metadata(
                        self.focal.scyon_id,
                        "living.focal",
                        key,
                        value,
                        "observed",
                    )

        return self.status()

    def _latest_observation(
        self,
        observation_kind: str,
    ) -> dict[str, Any] | None:
        row = (
            self.kernel.db.execute(
                """
                SELECT
                    payload_json,
                    digest,
                    recorded_at
                FROM event
                WHERE
                    scyon_id = ?
                    AND event_type = ?
                ORDER BY sequence DESC
                LIMIT 1
                """,
                (
                    self.focal.scyon_id,
                    (
                        "living.observation."
                        + observation_kind
                    ),
                ),
            ).fetchone()
        )

        if row is None:
            return None

        return {
            "payload": json.loads(
                row["payload_json"]
            ),
            "event_digest": (
                row["digest"]
            ),
            "recorded_at": (
                row["recorded_at"]
            ),
        }

    def observe(
        self,
        observation_kind: str,
        payload: dict[str, Any],
        *,
        source: str,
        source_digest: str | None = None,
        dependencies: list[str] | None = None,
        authority_state: str = "observed",
    ) -> dict[str, Any]:
        fingerprint = digest(
            {
                "kind": observation_kind,
                "payload": payload,
                "source": source,
                "source_digest": (
                    source_digest
                ),
            }
        )

        previous = (
            self._latest_observation(
                observation_kind
            )
        )

        if (
            previous
            and previous[
                "payload"
            ].get(
                "fingerprint"
            )
            == fingerprint
        ):
            return {
                "changed": False,
                "fingerprint": (
                    fingerprint
                ),
                "event_id": None,
                "previous_event_digest": (
                    previous[
                        "event_digest"
                    ]
                ),
            }

        previous_fingerprint = (
            previous[
                "payload"
            ].get(
                "fingerprint"
            )
            if previous
            else None
        )

        event_payload = {
            "fingerprint": fingerprint,
            "previous_fingerprint": (
                previous_fingerprint
            ),
            "source": source,
            "source_digest": (
                source_digest
            ),
            "observation": payload,
        }

        with (
            self.locked(),
            self.kernel.db,
        ):
            event_id = (
                self.kernel.append_event(
                    self.focal.scyon_id,
                    (
                        "living.observation."
                        + observation_kind
                    ),
                    event_payload,
                    authority={
                        "state": (
                            authority_state
                        ),
                        "authoritative": (
                            False
                        ),
                    },
                    lineage={
                        "created_by": (
                            self.focal.engine_id
                        ),
                        "depends_on": sorted(
                            dependencies
                            or []
                        ),
                        "previous_fingerprint": (
                            previous_fingerprint
                        ),
                    },
                    graph={
                        "source_node": (
                            self.focal.scyon_id
                        ),
                        "relation": (
                            "observes"
                        ),
                        "target_node": (
                            source
                        ),
                    },
                    provenance={
                        "engine_id": (
                            self.focal.engine_id
                        ),
                        "focal_id": (
                            self.focal.focal_id
                        ),
                        "source": (
                            source
                        ),
                        "source_digest": (
                            source_digest
                        ),
                    },
                )
            )

        return {
            "changed": True,
            "fingerprint": fingerprint,
            "event_id": event_id,
            "previous_event_digest": (
                previous[
                    "event_digest"
                ]
                if previous
                else None
            ),
        }

    def checkpoint(
        self,
    ) -> dict[str, Any]:
        validation = (
            self.kernel.validate()
        )

        counts: dict[
            str,
            int,
        ] = {}

        for table in (
            "metadata",
            "ability",
            "event",
            "branch",
        ):
            counts[
                table
            ] = self.kernel.db.execute(
                (
                    f"SELECT COUNT(*) "
                    f"FROM {table} "
                    f"WHERE scyon_id = ?"
                ),
                (
                    self.focal.scyon_id,
                ),
            ).fetchone()[0]

        latest = (
            self.kernel.db.execute(
                """
                SELECT
                    event_id,
                    event_type,
                    digest,
                    recorded_at
                FROM event
                WHERE scyon_id = ?
                ORDER BY sequence DESC
                LIMIT 1
                """,
                (
                    self.focal.scyon_id,
                ),
            ).fetchone()
        )

        return {
            "schema": (
                "savant://runtime/scyon/"
                "living-checkpoint/1.0.0"
            ),
            "engine_id": (
                self.focal.engine_id
            ),
            "focal_id": (
                self.focal.focal_id
            ),
            "scyon": (
                self.kernel.profile(
                    self.focal.scyon_id
                )
            ),
            "counts": counts,
            "latest_event": (
                dict(latest)
                if latest
                else None
            ),
            "validation": (
                validation
            ),
            "policy": (
                self.focal.policy
            ),
            "enhancement_count": len(
                self.focal.enhancements
            ),
        }

    def project(
        self,
        path: Path,
    ) -> dict[str, Any]:
        checkpoint = (
            self.checkpoint()
        )

        projection = {
            "schema": (
                "savant://projection/"
                "living-engine/1.0.0"
            ),
            "authority_state": (
                "projection"
            ),
            "rebuildable": True,
            "source_scyon": (
                self.focal.scyon_id
            ),
            "source_checkpoint_digest": (
                digest(
                    checkpoint
                )
            ),
            "checkpoint": checkpoint,
        }

        atomic_json(
            path,
            projection,
        )

        return projection

    def status(
        self,
    ) -> dict[str, Any]:
        profile = (
            self.kernel.profile(
                self.focal.scyon_id
            )
        )

        validation = (
            self.kernel.validate()
        )

        return {
            "engine_id": (
                self.focal.engine_id
            ),
            "focal_id": (
                self.focal.focal_id
            ),
            "scyon_id": (
                self.focal.scyon_id
            ),
            "owner": (
                self.focal.owner_id
            ),
            "owner_tier": (
                self.focal.owner_tier
            ),
            "living": (
                validation[
                    "valid"
                ]
            ),
            "mutation_authorized": (
                False
            ),
            "physical_migration_authorized": (
                False
            ),
            "kernel_digest": (
                profile["digest"]
            ),
            "enhancement_count": len(
                self.focal.enhancements
            ),
            "validation": (
                validation
            ),
        }


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Purpose-neutral Scyon "
            "living-engine layer"
        )
    )

    parser.add_argument(
        "--focal",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--database",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
    )

    parser.add_argument(
        "command",
        choices=(
            "bootstrap",
            "status",
            "checkpoint",
        ),
    )

    return parser


def main(
) -> int:
    arguments = (
        build_parser().parse_args()
    )

    focal = (
        LivingFocal.from_path(
            arguments.focal.resolve()
        )
    )

    with LivingEngine(
        focal,
        arguments.database.resolve(),
        root=arguments.root.resolve(),
    ) as engine:
        if (
            arguments.command
            == "bootstrap"
        ):
            result = (
                engine.bootstrap()
            )

        elif (
            arguments.command
            == "checkpoint"
        ):
            engine.bootstrap()

            result = (
                engine.checkpoint()
            )

        else:
            engine.bootstrap()

            result = (
                engine.status()
            )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        LivingEngineError,
    ) as exc:
        print(
            (
                "ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=os.sys.stderr,
        )

        raise SystemExit(1)
