#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")

GRAPH_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

SEED_PATH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.seed.json"
)

COLLECTION_ROOT = (
    ROOT
    / "authority"
    / "task-graph"
)

SNAPSHOT_ROOT = (
    COLLECTION_ROOT
    / "snapshots"
)

REPLAY_ROOT = (
    ROOT
    / "runtime"
    / "masterplan"
    / "replay"
)

REPORT_ROOT = (
    ROOT
    / "reports"
    / "niche"
    / "masterplan"
    / "replay"
)

BACKUP_ROOT = (
    ROOT
    / "backups"
    / "masterplan"
    / "replay"
)

AUTHORITATIVE_COLLECTIONS = (
    "events",
    "decisions",
    "evidence",
    "receipts",
    "attestations",
)

VOLATILE_FIELDS = {
    "generated_at",
    "created_at",
    "captured_at",
    "accepted_at",
    "occurred_at",
    "issued_at",
    "expires_at",
    "timestamp",
    "started_at",
    "finished_at",
    "duration_seconds",
    "elapsed_seconds",
    "wall_clock_seconds",
}


class ReplayError(RuntimeError):
    pass


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def timestamp() -> str:
    return dt.datetime.now(
        dt.timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")


def canonical_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def deterministic_projection(
    value: Any,
) -> Any:
    if isinstance(value, dict):
        return {
            key: deterministic_projection(child)
            for key, child in sorted(
                value.items(),
                key=lambda item: item[0],
            )
            if key not in VOLATILE_FIELDS
        }

    if isinstance(value, list):
        return [
            deterministic_projection(child)
            for child in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deterministic_projection(child)
            for child in value
        )

    return value


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            deterministic_projection(value)
        )
    ).hexdigest()


def sha256_path(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(value, dict):
        raise ReplayError(
            f"Expected JSON object: {path}"
        )

    return value


def atomic_write_text(
    path: Path,
    value: str,
    mode: int = 0o644,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def relative_path(
    path: Path,
) -> str:
    try:
        return path.relative_to(
            ROOT
        ).as_posix()

    except ValueError:
        return str(path)


def stable_records(
    values: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        values,
        key=lambda record: str(
            record.get(
                "id",
                "",
            )
        ),
    )


def validate_unique_ids(
    name: str,
    values: list[dict[str, Any]],
) -> None:
    seen: set[str] = set()

    for record in values:
        identifier = record.get(
            "id"
        )

        if not isinstance(
            identifier,
            str,
        ):
            raise ReplayError(
                (
                    f"{name} record has no "
                    "string identifier."
                )
            )

        if identifier in seen:
            raise ReplayError(
                (
                    f"Duplicate {name} "
                    f"identifier: {identifier}"
                )
            )

        seen.add(identifier)


def load_external_collection(
    name: str,
) -> list[dict[str, Any]]:
    root = (
        COLLECTION_ROOT
        / name
    )

    if not root.is_dir():
        return []

    values: list[
        dict[str, Any]
    ] = []

    for path in sorted(
        root.glob("*.json"),
        key=lambda candidate: (
            candidate.name
        ),
    ):
        if path.name in {
            "latest.json",
            "registry.json",
        }:
            continue

        value = load_json(path)

        values.append(value)

    validate_unique_ids(
        name,
        values,
    )

    return stable_records(
        values
    )


def merge_collection(
    embedded: Any,
    external: list[dict[str, Any]],
    name: str,
) -> list[dict[str, Any]]:
    if not isinstance(
        embedded,
        list,
    ):
        raise ReplayError(
            (
                "Embedded graph collection "
                f"is invalid: {name}"
            )
        )

    merged: dict[
        str,
        dict[str, Any],
    ] = {}

    for record in [
        *embedded,
        *external,
    ]:
        if not isinstance(
            record,
            dict,
        ):
            raise ReplayError(
                (
                    f"Invalid {name} "
                    "record during replay."
                )
            )

        identifier = record.get(
            "id"
        )

        if not isinstance(
            identifier,
            str,
        ):
            raise ReplayError(
                (
                    f"{name} record has "
                    "no string identifier."
                )
            )

        existing = merged.get(
            identifier
        )

        if (
            existing is not None
            and digest(existing)
            != digest(record)
        ):
            raise ReplayError(
                (
                    f"Conflicting {name} "
                    f"record: {identifier}"
                )
            )

        merged[
            identifier
        ] = record

    return stable_records(
        list(
            merged.values()
        )
    )


def choose_base() -> tuple[
    Path,
    dict[str, Any],
    str,
]:
    if SEED_PATH.is_file():
        seed = load_json(
            SEED_PATH
        )

        authoritative = load_json(
            GRAPH_PATH
        )

        seed_record_ids = {
            record.get("id")
            for record in seed.get(
                "records",
                [],
            )
            if isinstance(
                record,
                dict,
            )
        }

        authoritative_record_ids = {
            record.get("id")
            for record in authoritative.get(
                "records",
                [],
            )
            if isinstance(
                record,
                dict,
            )
        }

        seed_segue_ids = {
            record.get("id")
            for record in seed.get(
                "segues",
                [],
            )
            if isinstance(
                record,
                dict,
            )
        }

        authoritative_segue_ids = {
            record.get("id")
            for record in authoritative.get(
                "segues",
                [],
            )
            if isinstance(
                record,
                dict,
            )
        }

        if (
            seed_record_ids
            == authoritative_record_ids
            and seed_segue_ids
            == authoritative_segue_ids
        ):
            return (
                SEED_PATH,
                seed,
                "authoritative_seed",
            )

    authoritative = load_json(
        GRAPH_PATH
    )

    return (
        GRAPH_PATH,
        authoritative,
        "authoritative_graph_baseline",
    )


def replay_graph() -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    if not GRAPH_PATH.is_file():
        raise FileNotFoundError(
            GRAPH_PATH
        )

    base_path, base, base_mode = (
        choose_base()
    )

    replayed = json.loads(
        json.dumps(base)
    )

    for collection in (
        AUTHORITATIVE_COLLECTIONS
    ):
        external = (
            load_external_collection(
                collection
            )
        )

        replayed[
            collection
        ] = merge_collection(
            replayed.get(
                collection,
                [],
            ),
            external,
            collection,
        )

    authoritative = load_json(
        GRAPH_PATH
    )

    comparison_collections = (
        "records",
        "segues",
        *AUTHORITATIVE_COLLECTIONS,
    )

    comparison: dict[
        str,
        Any,
    ] = {}

    for collection in (
        comparison_collections
    ):
        replayed_values = (
            replayed.get(
                collection,
                [],
            )
        )

        authoritative_values = (
            authoritative.get(
                collection,
                [],
            )
        )

        if not isinstance(
            replayed_values,
            list,
        ):
            raise ReplayError(
                (
                    "Replayed collection "
                    f"is invalid: {collection}"
                )
            )

        if not isinstance(
            authoritative_values,
            list,
        ):
            raise ReplayError(
                (
                    "Authoritative collection "
                    f"is invalid: {collection}"
                )
            )

        replayed_normalized = (
            stable_records(
                replayed_values
            )
        )

        authoritative_normalized = (
            stable_records(
                authoritative_values
            )
        )

        replayed[
            collection
        ] = replayed_normalized

        comparison[
            collection
        ] = {
            "passed": (
                digest(
                    replayed_normalized
                )
                == digest(
                    authoritative_normalized
                )
            ),
            "replayed_count": len(
                replayed_normalized
            ),
            "authoritative_count": len(
                authoritative_normalized
            ),
            "replayed_digest": digest(
                replayed_normalized
            ),
            "authoritative_digest": (
                digest(
                    authoritative_normalized
                )
            ),
        }

    replayed_digest = digest(
        replayed
    )

    authoritative_digest = digest(
        authoritative
    )

    metadata = {
        "base": {
            "path": relative_path(
                base_path
            ),
            "mode": base_mode,
            "sha256": sha256_path(
                base_path
            ),
            "digest": digest(base),
        },
        "comparison": {
            "passed": (
                replayed_digest
                == authoritative_digest
                and all(
                    value["passed"]
                    for value
                    in comparison.values()
                )
            ),
            "replayed_digest": (
                replayed_digest
            ),
            "authoritative_digest": (
                authoritative_digest
            ),
            "collections": comparison,
        },
    }

    return replayed, metadata


def persist_replay(
    replayed: dict[str, Any],
    metadata: dict[str, Any],
    *,
    apply: bool,
) -> dict[str, Any]:
    REPLAY_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_id = timestamp()

    replay_path = (
        REPLAY_ROOT
        / f"{run_id}__masterplan.json"
    )

    latest_path = (
        REPLAY_ROOT
        / "latest.json"
    )

    atomic_write_json(
        replay_path,
        replayed,
    )

    atomic_write_json(
        latest_path,
        replayed,
    )

    backup = None
    snapshot = None

    if apply:
        if not metadata[
            "comparison"
        ][
            "passed"
        ]:
            raise ReplayError(
                (
                    "Replay cannot be applied "
                    "because parity failed."
                )
            )

        backup = (
            BACKUP_ROOT
            / run_id
            / "masterplan.json"
        )

        backup.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            GRAPH_PATH,
            backup,
        )

        atomic_write_json(
            GRAPH_PATH,
            replayed,
        )

        SNAPSHOT_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        snapshot = (
            SNAPSHOT_ROOT
            / (
                f"{run_id}__"
                "masterplan-replay.json"
            )
        )

        atomic_write_json(
            snapshot,
            replayed,
        )

    result: dict[str, Any] = {
        "schema": (
            "savant://niche/masterplan/"
            "graph-replay/1.1.0"
        ),
        "operation": (
            "replay_masterplan_graph"
        ),
        "generated_at": utc_now(),
        "passed": metadata[
            "comparison"
        ][
            "passed"
        ],
        "applied": apply,
        "base": metadata[
            "base"
        ],
        "replay": {
            "path": relative_path(
                latest_path
            ),
            "historical_path": (
                relative_path(
                    replay_path
                )
            ),
            "sha256": sha256_path(
                latest_path
            ),
            "digest": digest(
                replayed
            ),
        },
        "comparison": metadata[
            "comparison"
        ],
        "backup": (
            relative_path(backup)
            if backup is not None
            else None
        ),
        "snapshot": (
            relative_path(snapshot)
            if snapshot is not None
            else None
        ),
    }

    result["digest"] = digest(
        result
    )

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    atomic_write_json(
        REPORT_ROOT
        / f"{run_id}__replay.json",
        result,
    )

    atomic_write_json(
        REPORT_ROOT
        / "latest.json",
        result,
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministically replay the "
            "authoritative Masterplan graph."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        replayed, metadata = (
            replay_graph()
        )

        result = persist_replay(
            replayed,
            metadata,
            apply=arguments.apply,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "operation": (
                        "replay_masterplan_graph"
                    ),
                    "passed": False,
                    "error": {
                        "type": type(
                            exc
                        ).__name__,
                        "message": str(
                            exc
                        ),
                    },
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        arguments.strict
        and not result[
            "passed"
        ]
    ):
        return 1

    return (
        0
        if result["passed"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
