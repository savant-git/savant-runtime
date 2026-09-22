#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any


schema = "savant.living-projection.v1"

runtime_root = Path(
    "/root/savant-runtime"
).resolve()

living_root = (
    runtime_root
    / "runtime"
    / "living-projection"
).resolve()

projection_path = (
    living_root
    / "current.json"
)

health_path = (
    living_root
    / "health.json"
)

history_path = (
    living_root
    / "history.jsonl"
)

governance_root = (
    runtime_root
    / "canon-system"
    / "projections"
    / "living"
)

governance_status_path = (
    governance_root
    / "status.json"
)

governance_snapshot_path = (
    governance_root
    / "snapshot.json"
)

governance_graph_path = (
    governance_root
    / "graph.json"
)

living_state_root = (
    runtime_root
    / "runtime"
    / "living-state"
)

living_state_path = (
    living_state_root
    / "current.json"
)

living_state_health_path = (
    living_state_root
    / "health.json"
)

niche_projection_root = (
    runtime_root
    / "runtime"
    / "niche"
    / "projections"
)

masterplan_json_path = (
    runtime_root
    / "masterplan.json"
)

masterplan_markdown_path = (
    runtime_root
    / "MASTERPLAN.md"
)

structure_candidates = (
    runtime_root
    / "SAVANT_STRUCTURE_CURRENT.md",
    runtime_root
    / "structure.json",
)

canon_candidates = (
    runtime_root
    / "canon-system"
    / "projections",
    runtime_root
    / "canon-system"
    / "authority",
)

stream_owners = {
    "canon": "lore",
    "structure": "scyon",
    "masterplan": "niche",
    "terminology": "living-governance",
    "rules": "living-governance",
    "decisions": "living-governance",
    "permissions": "living-governance",
    "invariants": "living-governance",
    "compatibility": "living-governance",
    "risks": "living-governance",
    "enhancements": "living-governance",
    "unknowns": "living-governance",
    "dependencies": "living-governance",
    "provenance": "living-governance",
    "assurance": "living-state",
    "context": "projection",
    "implementation": "living-state",
    "evidence": "living-state",
    "evolution": "projection",
}

governance_streams = frozenset(
    {
        "compatibility",
        "decisions",
        "enhancements",
        "invariants",
        "masterplan",
        "permissions",
        "risks",
        "rules",
        "structure",
        "terminology",
        "unknowns",
    }
)


def compact_json(
    value: Any,
) -> str:
    try:
        import orjson

        return orjson.dumps(
            value,
            option=orjson.OPT_SORT_KEYS,
        ).decode(
            "utf-8"
        )

    except ImportError:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )


def pretty_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )


def stable_hash(
    value: Any,
) -> str:
    try:
        import blake3

        return blake3.blake3(
            compact_json(
                value
            ).encode(
                "utf-8"
            )
        ).hexdigest()

    except ImportError:
        return hashlib.sha256(
            compact_json(
                value
            ).encode(
                "utf-8"
            )
        ).hexdigest()


def read_json(
    path: Path,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(
            value,
            dict,
        ):
            return value

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return {}


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".partial",
        dir=str(
            path.parent
        ),
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            handle.write(
                pretty_json(
                    value
                )
            )
            handle.write(
                "\n"
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary,
            0o600,
        )

        os.replace(
            temporary,
            path,
        )

    finally:
        if temporary.exists():
            temporary.unlink()


def append_history(
    value: dict[str, Any],
) -> None:
    living_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    with history_path.open(
        "a",
        encoding="utf-8",
        newline="",
    ) as handle:
        handle.write(
            compact_json(
                value
            )
        )
        handle.write(
            "\n"
        )
        handle.flush()
        os.fsync(
            handle.fileno()
        )


def file_state(
    path: Path,
    include_hash: bool = True,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(
            path
        ),
        "present": False,
        "authority_effect": "none",
    }

    try:
        info = path.stat()

    except OSError:
        return record

    record.update(
        {
            "present": path.is_file(),
            "mtime_ns": info.st_mtime_ns,
            "size": info.st_size,
        }
    )

    if (
        include_hash
        and path.is_file()
    ):
        digest = hashlib.sha256()

        try:
            with path.open(
                "rb"
            ) as handle:
                while True:
                    chunk = handle.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    digest.update(
                        chunk
                    )

            record[
                "sha256"
            ] = digest.hexdigest()

        except OSError:
            record[
                "sha256"
            ] = None

    return record


def directory_state(
    path: Path,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(
            path
        ),
        "present": path.is_dir(),
        "files": 0,
        "directories": 0,
        "bytes": 0,
        "newest_mtime_ns": None,
        "authority_effect": "none",
    }

    if not path.is_dir():
        return record

    newest = 0

    try:
        for root, directories, filenames in os.walk(
            path
        ):
            record[
                "directories"
            ] += len(
                directories
            )

            for name in filenames:
                candidate = (
                    Path(
                        root
                    )
                    / name
                )

                try:
                    info = candidate.stat()

                except OSError:
                    continue

                if not candidate.is_file():
                    continue

                record[
                    "files"
                ] += 1

                record[
                    "bytes"
                ] += info.st_size

                newest = max(
                    newest,
                    info.st_mtime_ns,
                )

    except OSError:
        pass

    record[
        "newest_mtime_ns"
    ] = (
        newest
        if newest
        else None
    )

    return record


def projection_age_seconds(
    mtime_ns: int | None,
) -> float | None:
    if not mtime_ns:
        return None

    return max(
        0.0,
        (
            time.time_ns()
            - mtime_ns
        )
        / 1_000_000_000,
    )


def freshness(
    mtime_ns: int | None,
) -> dict[str, Any]:
    age = projection_age_seconds(
        mtime_ns
    )

    if age is None:
        state = "absent"

    elif age <= 30:
        state = "hot"

    elif age <= 300:
        state = "current"

    elif age <= 3600:
        state = "aging"

    else:
        state = "stale"

    return {
        "state": state,
        "age_seconds": age,
    }


def governance_records() -> list[dict[str, Any]]:
    snapshot = read_json(
        governance_snapshot_path
    )

    records = snapshot.get(
        "records",
        []
    )

    if not isinstance(
        records,
        list,
    ):
        return []

    return [
        record
        for record
        in records
        if isinstance(
            record,
            dict,
        )
    ]


def records_for_stream(
    records: list[dict[str, Any]],
    stream: str,
) -> list[dict[str, Any]]:
    return [
        record
        for record
        in records
        if record.get(
            "stream"
        ) == stream
    ]


def authority_summary(
    records: list[dict[str, Any]],
) -> dict[str, int]:
    result: dict[str, int] = {}

    for record in records:
        authority = str(
            record.get(
                "authority",
                "unknown",
            )
        )

        result[
            authority
        ] = (
            result.get(
                authority,
                0,
            )
            + 1
        )

    return dict(
        sorted(
            result.items()
        )
    )


def source_summary(
    records: list[dict[str, Any]],
) -> dict[str, int]:
    result: dict[str, int] = {}

    for record in records:
        provenance = record.get(
            "provenance"
        )

        if isinstance(
            provenance,
            dict,
        ):
            source = str(
                provenance.get(
                    "source",
                    provenance.get(
                        "kind",
                        "unspecified",
                    ),
                )
            )

        elif provenance:
            source = str(
                provenance
            )

        else:
            source = "unspecified"

        result[
            source
        ] = (
            result.get(
                source,
                0,
            )
            + 1
        )

    return dict(
        sorted(
            result.items()
        )
    )


def dependency_summary(
    graph: dict[str, Any],
) -> dict[str, Any]:
    nodes = graph.get(
        "nodes",
        []
    )

    edges = graph.get(
        "edges",
        []
    )

    reverse_dependencies = graph.get(
        "reverse_dependencies",
        {}
    )

    if not isinstance(
        nodes,
        list,
    ):
        nodes = []

    if not isinstance(
        edges,
        list,
    ):
        edges = []

    if not isinstance(
        reverse_dependencies,
        dict,
    ):
        reverse_dependencies = {}

    return {
        "nodes": len(
            nodes
        ),
        "edges": len(
            edges
        ),
        "reverse_dependency_roots": len(
            reverse_dependencies
        ),
        "records": {
            "nodes": nodes,
            "edges": edges,
            "reverse_dependencies":
                reverse_dependencies,
        },
    }


def stream_projection(
    stream: str,
    records: list[dict[str, Any]],
    governance_status: dict[str, Any],
) -> dict[str, Any]:
    selected = records_for_stream(
        records,
        stream,
    )

    digest = stable_hash(
        selected
    )

    return {
        "schema":
            "savant.living-projection.stream.v1",
        "id":
            f"living:{stream}",
        "kind":
            stream,
        "owner":
            stream_owners.get(
                stream,
                "living-governance",
            ),
        "projection_only":
            True,
        "authority_effect":
            "none",
        "record_count":
            len(
                selected
            ),
        "records":
            selected,
        "authority":
            authority_summary(
                selected
            ),
        "provenance":
            source_summary(
                selected
            ),
        "digest":
            digest,
        "governance_digest":
            governance_status.get(
                "digest"
            ),
        "conflict_count":
            governance_status.get(
                "conflict_count",
                0,
            ),
    }


def canon_projection() -> dict[str, Any]:
    sources = [
        directory_state(
            path
        )
        for path
        in canon_candidates
    ]

    return {
        "schema":
            "savant.living-projection.canon.v1",
        "id":
            "living:canon",
        "owner":
            stream_owners[
                "canon"
            ],
        "projection_only":
            True,
        "authority_effect":
            "none",
        "filesystem_presence_establishes_authority":
            False,
        "sources":
            sources,
        "digest":
            stable_hash(
                sources
            ),
        "note":
            (
                "filesystem observation only; "
                "canon authority remains with its owner"
            ),
    }


def structure_projection(
    records: list[dict[str, Any]],
    governance_status: dict[str, Any],
) -> dict[str, Any]:
    projection = stream_projection(
        "structure",
        records,
        governance_status,
    )

    sources = [
        file_state(
            path
        )
        for path
        in structure_candidates
    ]

    projection.update(
        {
            "owner":
                stream_owners[
                    "structure"
                ],
            "sources":
                sources,
            "source_digest":
                stable_hash(
                    sources
                ),
        }
    )

    return projection


def masterplan_projection(
    records: list[dict[str, Any]],
    governance_status: dict[str, Any],
) -> dict[str, Any]:
    projection = stream_projection(
        "masterplan",
        records,
        governance_status,
    )

    sources = [
        file_state(
            masterplan_json_path
        ),
        file_state(
            masterplan_markdown_path
        ),
        directory_state(
            niche_projection_root
        ),
    ]

    projection.update(
        {
            "owner":
                stream_owners[
                    "masterplan"
                ],
            "sources":
                sources,
            "source_digest":
                stable_hash(
                    sources
                ),
        }
    )

    return projection


def assurance_projection(
    living_state: dict[str, Any],
    living_health: dict[str, Any],
) -> dict[str, Any]:
    filesystem = living_state.get(
        "filesystem",
        {}
    )

    delta = living_state.get(
        "delta",
        {}
    )

    services = living_state.get(
        "services",
        []
    )

    processes = living_state.get(
        "processes",
        []
    )

    ports = living_state.get(
        "listening_tcp",
        []
    )

    if not isinstance(
        filesystem,
        dict,
    ):
        filesystem = {}

    if not isinstance(
        delta,
        dict,
    ):
        delta = {}

    if not isinstance(
        services,
        list,
    ):
        services = []

    if not isinstance(
        processes,
        list,
    ):
        processes = []

    if not isinstance(
        ports,
        list,
    ):
        ports = []

    active_services = sum(
        1
        for service
        in services
        if isinstance(
            service,
            dict,
        )
        and service.get(
            "active_state"
        ) == "active"
    )

    return {
        "schema":
            "savant.living-projection.assurance.v1",
        "id":
            "living:assurance",
        "owner":
            stream_owners[
                "assurance"
            ],
        "projection_only":
            True,
        "authority_effect":
            "none",
        "healthy":
            living_health.get(
                "healthy",
                False,
            ),
        "sequence":
            living_state.get(
                "sequence"
            ),
        "snapshot_hash":
            living_state.get(
                "snapshot_hash"
            ),
        "previous_snapshot_hash":
            living_state.get(
                "previous_snapshot_hash"
            ),
        "filesystem": {
            "files":
                filesystem.get(
                    "files",
                    0,
                ),
            "source_candidates":
                filesystem.get(
                    "source_candidates",
                    0,
                ),
            "bytes":
                filesystem.get(
                    "bytes",
                    0,
                ),
            "failure_count":
                len(
                    filesystem.get(
                        "failures",
                        [],
                    )
                ),
            "evidence_classes":
                filesystem.get(
                    "evidence_classes",
                    {},
                ),
        },
        "delta":
            delta,
        "services": {
            "known":
                len(
                    services
                ),
            "active":
                active_services,
        },
        "process_count":
            len(
                processes
            ),
        "listening_tcp_count":
            len(
                ports
            ),
        "capabilities":
            living_state.get(
                "capabilities",
                {},
            ),
    }


def implementation_projection(
    living_state: dict[str, Any],
) -> dict[str, Any]:
    filesystem = living_state.get(
        "filesystem",
        {}
    )

    if not isinstance(
        filesystem,
        dict,
    ):
        filesystem = {}

    classes = filesystem.get(
        "evidence_classes",
        {}
    )

    if not isinstance(
        classes,
        dict,
    ):
        classes = {}

    return {
        "schema":
            "savant.living-projection.implementation.v1",
        "id":
            "living:implementation",
        "owner":
            stream_owners[
                "implementation"
            ],
        "projection_only":
            True,
        "authority_effect":
            "none",
        "implementation_evidence":
            classes.get(
                "implementation_evidence",
                0,
            ),
        "runtime_projection_or_state":
            classes.get(
                "runtime_projection_or_state",
                0,
            ),
        "migration_evidence":
            classes.get(
                "migration_evidence",
                0,
            ),
        "source_candidates":
            filesystem.get(
                "source_candidates",
                0,
            ),
        "latest_sdump":
            living_state.get(
                "latest_sdump"
            ),
        "git":
            living_state.get(
                "git"
            ),
        "packages":
            living_state.get(
                "packages",
                [],
            ),
    }


def evidence_projection(
    living_state: dict[str, Any],
) -> dict[str, Any]:
    filesystem = living_state.get(
        "filesystem",
        {}
    )

    if not isinstance(
        filesystem,
        dict,
    ):
        filesystem = {}

    classes = filesystem.get(
        "evidence_classes",
        {}
    )

    if not isinstance(
        classes,
        dict,
    ):
        classes = {}

    return {
        "schema":
            "savant.living-projection.evidence.v1",
        "id":
            "living:evidence",
        "owner":
            stream_owners[
                "evidence"
            ],
        "projection_only":
            True,
        "authority_effect":
            "none",
        "classes":
            classes,
        "authority_candidates":
            classes.get(
                "authority_candidate",
                0,
            ),
        "backup_evidence":
            classes.get(
                "backup_evidence",
                0,
            ),
        "historical_evidence":
            classes.get(
                "imported_or_historical_evidence",
                0,
            ),
        "migration_evidence":
            classes.get(
                "migration_evidence",
                0,
            ),
        "vault_evidence":
            classes.get(
                "vault_evidence",
                0,
            ),
    }


def evolution_projection(
    living_state: dict[str, Any],
) -> dict[str, Any]:
    delta = living_state.get(
        "delta",
        {}
    )

    if not isinstance(
        delta,
        dict,
    ):
        delta = {}

    return {
        "schema":
            "savant.living-projection.evolution.v1",
        "id":
            "living:evolution",
        "owner":
            stream_owners[
                "evolution"
            ],
        "projection_only":
            True,
        "authority_effect":
            "none",
        "sequence":
            living_state.get(
                "sequence"
            ),
        "snapshot_hash":
            living_state.get(
                "snapshot_hash"
            ),
        "previous_snapshot_hash":
            living_state.get(
                "previous_snapshot_hash"
            ),
        "added":
            delta.get(
                "added",
                [],
            ),
        "changed":
            delta.get(
                "changed",
                [],
            ),
        "deleted":
            delta.get(
                "deleted",
                [],
            ),
        "added_count":
            delta.get(
                "added_count",
                0,
            ),
        "changed_count":
            delta.get(
                "changed_count",
                0,
            ),
        "deleted_count":
            delta.get(
                "deleted_count",
                0,
            ),
    }


def context_projection(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    identifiers = sorted(
        {
            str(
                record.get(
                    "id"
                )
            )
            for record
            in records
            if record.get(
                "id"
            )
        }
    )

    streams = sorted(
        {
            str(
                record.get(
                    "stream"
                )
            )
            for record
            in records
            if record.get(
                "stream"
            )
        }
    )

    return {
        "schema":
            "savant.living-projection.context.v1",
        "id":
            "living:context",
        "owner":
            stream_owners[
                "context"
            ],
        "projection_only":
            True,
        "authority_effect":
            "none",
        "record_count":
            len(
                records
            ),
        "streams":
            streams,
        "identifiers":
            identifiers,
        "digest":
            stable_hash(
                {
                    "streams":
                        streams,
                    "identifiers":
                        identifiers,
                }
            ),
    }


def build_projection() -> dict[str, Any]:
    previous = read_json(
        projection_path
    )

    governance_status = read_json(
        governance_status_path
    )

    governance_graph = read_json(
        governance_graph_path
    )

    living_state = read_json(
        living_state_path
    )

    living_health = read_json(
        living_state_health_path
    )

    records = governance_records()

    sequence = (
        int(
            previous.get(
                "sequence",
                0,
            )
        )
        + 1
    )

    generated_at_ns = time.time_ns()

    surfaces: dict[str, Any] = {}

    surfaces[
        "canon"
    ] = canon_projection()

    surfaces[
        "structure"
    ] = structure_projection(
        records,
        governance_status,
    )

    surfaces[
        "masterplan"
    ] = masterplan_projection(
        records,
        governance_status,
    )

    for stream in sorted(
        governance_streams
        - {
            "structure",
            "masterplan",
        }
    ):
        surfaces[
            stream
        ] = stream_projection(
            stream,
            records,
            governance_status,
        )

    surfaces[
        "dependencies"
    ] = {
        "schema":
            "savant.living-projection.dependencies.v1",
        "id":
            "living:dependencies",
        "owner":
            stream_owners[
                "dependencies"
            ],
        "projection_only":
            True,
        "authority_effect":
            "none",
        **dependency_summary(
            governance_graph
        ),
    }

    surfaces[
        "provenance"
    ] = {
        "schema":
            "savant.living-projection.provenance.v1",
        "id":
            "living:provenance",
        "owner":
            stream_owners[
                "provenance"
            ],
        "projection_only":
            True,
        "authority_effect":
            "none",
        "sources":
            source_summary(
                records
            ),
        "authority":
            authority_summary(
                records
            ),
        "record_count":
            len(
                records
            ),
    }

    surfaces[
        "assurance"
    ] = assurance_projection(
        living_state,
        living_health,
    )

    surfaces[
        "context"
    ] = context_projection(
        records
    )

    surfaces[
        "implementation"
    ] = implementation_projection(
        living_state
    )

    surfaces[
        "evidence"
    ] = evidence_projection(
        living_state
    )

    surfaces[
        "evolution"
    ] = evolution_projection(
        living_state
    )

    surface_digests = {
        name:
            stable_hash(
                value
            )
        for name, value
        in surfaces.items()
    }

    previous_digests = previous.get(
        "surface_digests",
        {}
    )

    if not isinstance(
        previous_digests,
        dict,
    ):
        previous_digests = {}

    changed_surfaces = sorted(
        name
        for name, digest
        in surface_digests.items()
        if previous_digests.get(
            name
        ) != digest
    )

    unchanged_surfaces = sorted(
        name
        for name, digest
        in surface_digests.items()
        if previous_digests.get(
            name
        ) == digest
    )

    source_states = {
        "living_state":
            file_state(
                living_state_path,
                include_hash=False,
            ),
        "living_state_health":
            file_state(
                living_state_health_path,
                include_hash=False,
            ),
        "governance_status":
            file_state(
                governance_status_path,
                include_hash=False,
            ),
        "governance_snapshot":
            file_state(
                governance_snapshot_path,
                include_hash=False,
            ),
        "governance_graph":
            file_state(
                governance_graph_path,
                include_hash=False,
            ),
    }

    for source in source_states.values():
        source[
            "freshness"
        ] = freshness(
            source.get(
                "mtime_ns"
            )
        )

    projection = {
        "schema":
            schema,
        "sequence":
            sequence,
        "generated_at_unix_ns":
            generated_at_ns,
        "projection_only":
            True,
        "authority_effect":
            "none",
        "filesystem_presence_establishes_authority":
            False,
        "single_projection_fabric":
            True,
        "source_authority_preserved":
            True,
        "owners":
            stream_owners,
        "sources":
            source_states,
        "surface_count":
            len(
                surfaces
            ),
        "surfaces":
            surfaces,
        "surface_digests":
            surface_digests,
        "changed_surfaces":
            changed_surfaces,
        "unchanged_surfaces":
            unchanged_surfaces,
        "change_count":
            len(
                changed_surfaces
            ),
        "governance": {
            "digest":
                governance_status.get(
                    "digest"
                ),
            "ledger_present":
                governance_status.get(
                    "ledger_present",
                    False,
                ),
            "ledger_events":
                governance_status.get(
                    "ledger_events",
                    0,
                ),
            "current_records":
                governance_status.get(
                    "current_records",
                    len(
                        records
                    ),
                ),
            "conflict_count":
                governance_status.get(
                    "conflict_count",
                    0,
                ),
        },
        "living_state": {
            "healthy":
                living_health.get(
                    "healthy",
                    False,
                ),
            "sequence":
                living_state.get(
                    "sequence"
                ),
            "snapshot_hash":
                living_state.get(
                    "snapshot_hash"
                ),
        },
        "capabilities": {
            "atomic_publication":
                True,
            "content_hashing":
                True,
            "incremental_surface_diff":
                True,
            "deterministic_projection":
                True,
            "source_owner_preservation":
                True,
            "authority_separation":
                True,
            "provenance_projection":
                True,
            "dependency_projection":
                True,
            "reverse_dependency_projection":
                True,
            "temporal_sequence":
                True,
            "projection_history":
                True,
            "freshness_tracking":
                True,
            "staleness_detection":
                True,
            "last_known_projection":
                True,
            "failure_isolation":
                True,
            "health_projection":
                True,
            "change_reason_surface":
                True,
            "evidence_classification":
                True,
            "implementation_projection":
                True,
            "evolution_projection":
                True,
            "context_projection":
                True,
            "canon_projection":
                True,
            "structure_projection":
                True,
            "masterplan_projection":
                True,
            "governance_stream_projection":
                True,
            "assurance_projection":
                True,
            "blake3_when_available":
                True,
            "orjson_when_available":
                True,
            "secret_values_serialized":
                False,
        },
    }

    hash_material = dict(
        projection
    )

    projection[
        "projection_hash"
    ] = stable_hash(
        hash_material
    )

    projection[
        "previous_projection_hash"
    ] = previous.get(
        "projection_hash"
    )

    return projection


def persist_projection() -> dict[str, Any]:
    started = time.monotonic()

    try:
        projection = build_projection()

        atomic_write_json(
            projection_path,
            projection,
        )

        event = {
            "schema":
                "savant.living-projection.event.v1",
            "sequence":
                projection[
                    "sequence"
                ],
            "generated_at_unix_ns":
                projection[
                    "generated_at_unix_ns"
                ],
            "projection_hash":
                projection[
                    "projection_hash"
                ],
            "previous_projection_hash":
                projection.get(
                    "previous_projection_hash"
                ),
            "changed_surfaces":
                projection[
                    "changed_surfaces"
                ],
            "change_count":
                projection[
                    "change_count"
                ],
        }

        event[
            "event_hash"
        ] = stable_hash(
            event
        )

        append_history(
            event
        )

        health = {
            "schema":
                "savant.living-projection.health.v1",
            "healthy":
                True,
            "sequence":
                projection[
                    "sequence"
                ],
            "projection_hash":
                projection[
                    "projection_hash"
                ],
            "surface_count":
                projection[
                    "surface_count"
                ],
            "change_count":
                projection[
                    "change_count"
                ],
            "duration_seconds":
                (
                    time.monotonic()
                    - started
                ),
            "updated_at_unix_ns":
                time.time_ns(),
        }

        atomic_write_json(
            health_path,
            health,
        )

        return projection

    except Exception as error:
        atomic_write_json(
            health_path,
            {
                "schema":
                    "savant.living-projection.health.v1",
                "healthy":
                    False,
                "error":
                    type(
                        error
                    ).__name__,
                "message":
                    str(
                        error
                    ),
                "updated_at_unix_ns":
                    time.time_ns(),
            },
        )

        raise


def one_shot() -> int:
    projection = persist_projection()

    print(
        compact_json(
            {
                "ok":
                    True,
                "sequence":
                    projection[
                        "sequence"
                    ],
                "projection_hash":
                    projection[
                        "projection_hash"
                    ],
                "surface_count":
                    projection[
                        "surface_count"
                    ],
                "changed_surfaces":
                    projection[
                        "changed_surfaces"
                    ],
                "current":
                    str(
                        projection_path
                    ),
            }
        )
    )

    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="savant-living-projection",
    )

    value.add_argument(
        "--once",
        action="store_true",
    )

    return value


def main() -> int:
    arguments = parser().parse_args()

    living_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    if arguments.once:
        return one_shot()

    return one_shot()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
