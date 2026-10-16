#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import tempfile
import threading
import time
from typing import Any


schema = "savant.living-fabric.v1"

runtime_root = Path(
    "/root/savant-runtime"
).resolve()

fabric_root = (
    runtime_root
    / "runtime"
    / "living-fabric"
).resolve()

current_path = (
    fabric_root
    / "current.json"
)

health_path = (
    fabric_root
    / "health.json"
)

history_path = (
    fabric_root
    / "history.jsonl"
)

receipt_path = (
    fabric_root
    / "receipt.json"
)

base_projection_path = (
    runtime_root
    / "runtime"
    / "living-projection"
    / "current.json"
)

extension_projection_path = (
    runtime_root
    / "runtime"
    / "living-projection"
    / "extensions.json"
)

living_state_path = (
    runtime_root
    / "runtime"
    / "living-state"
    / "current.json"
)

living_state_health_path = (
    runtime_root
    / "runtime"
    / "living-state"
    / "health.json"
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

stop_event = threading.Event()


surface_catalog = {
    "canon": {
        "owner": "lore",
        "class": "substance",
        "mode": "projection",
    },
    "structure": {
        "owner": "scyon",
        "class": "structure",
        "mode": "projection",
    },
    "masterplan": {
        "owner": "niche",
        "class": "coordination",
        "mode": "projection",
    },
    "sdump": {
        "owner": "existing-living-sdump",
        "class": "observation",
        "mode": "reference",
    },
    "persona": {
        "owner": "envoy",
        "class": "persona",
        "mode": "projection",
    },
    "persona_traits": {
        "owner": "envoy",
        "class": "persona",
        "mode": "projection",
    },
    "persona_trait_state": {
        "owner": "envoy",
        "class": "persona",
        "mode": "derived",
    },
    "persona_trait_history": {
        "owner": "envoy",
        "class": "persona",
        "mode": "derived",
    },
    "persona_trait_candidates": {
        "owner": "envoy",
        "class": "persona",
        "mode": "derived",
    },
    "persona_trait_evidence": {
        "owner": "envoy",
        "class": "persona",
        "mode": "derived",
    },
    "persona_trait_evaluation": {
        "owner": "envoy",
        "class": "persona",
        "mode": "derived",
    },
    "persona_trait_adjudication": {
        "owner": "envoy",
        "class": "persona",
        "mode": "derived",
    },
    "persona_trait_experiment": {
        "owner": "envoy",
        "class": "persona",
        "mode": "derived",
    },
    "terminology": {
        "owner": "living-governance",
        "class": "governance",
        "mode": "projection",
    },
    "rules": {
        "owner": "living-governance",
        "class": "governance",
        "mode": "projection",
    },
    "decisions": {
        "owner": "living-governance",
        "class": "governance",
        "mode": "projection",
    },
    "permissions": {
        "owner": "living-governance",
        "class": "governance",
        "mode": "projection",
    },
    "invariants": {
        "owner": "living-governance",
        "class": "governance",
        "mode": "projection",
    },
    "compatibility": {
        "owner": "living-governance",
        "class": "governance",
        "mode": "projection",
    },
    "risks": {
        "owner": "living-governance",
        "class": "governance",
        "mode": "projection",
    },
    "enhancements": {
        "owner": "living-governance",
        "class": "governance",
        "mode": "projection",
    },
    "unknowns": {
        "owner": "living-governance",
        "class": "governance",
        "mode": "projection",
    },
    "dependencies": {
        "owner": "living-governance",
        "class": "graph",
        "mode": "projection",
    },
    "dependents": {
        "owner": "living-governance",
        "class": "graph",
        "mode": "derived",
    },
    "provenance": {
        "owner": "living-governance",
        "class": "lineage",
        "mode": "projection",
    },
    "lineage": {
        "owner": "living-governance",
        "class": "lineage",
        "mode": "derived",
    },
    "authority": {
        "owner": "living-governance",
        "class": "authority",
        "mode": "derived",
    },
    "conflicts": {
        "owner": "living-governance",
        "class": "authority",
        "mode": "derived",
    },
    "supersession": {
        "owner": "living-governance",
        "class": "authority",
        "mode": "derived",
    },
    "assurance": {
        "owner": "living-state",
        "class": "assurance",
        "mode": "projection",
    },
    "implementation": {
        "owner": "living-state",
        "class": "implementation",
        "mode": "projection",
    },
    "evidence": {
        "owner": "living-state",
        "class": "evidence",
        "mode": "projection",
    },
    "evolution": {
        "owner": "living-state",
        "class": "evolution",
        "mode": "projection",
    },
    "context": {
        "owner": "living-fabric",
        "class": "context",
        "mode": "derived",
    },
    "filesystem": {
        "owner": "living-state",
        "class": "observation",
        "mode": "derived",
    },
    "services": {
        "owner": "living-state",
        "class": "runtime",
        "mode": "derived",
    },
    "processes": {
        "owner": "living-state",
        "class": "runtime",
        "mode": "derived",
    },
    "network": {
        "owner": "living-state",
        "class": "runtime",
        "mode": "derived",
    },
    "system": {
        "owner": "living-state",
        "class": "runtime",
        "mode": "derived",
    },
    "packages": {
        "owner": "living-state",
        "class": "implementation",
        "mode": "derived",
    },
    "git": {
        "owner": "living-state",
        "class": "implementation",
        "mode": "derived",
    },
    "datastores": {
        "owner": "living-state",
        "class": "runtime",
        "mode": "derived",
    },
    "environment": {
        "owner": "living-state",
        "class": "runtime",
        "mode": "derived",
    },
    "capabilities": {
        "owner": "living-fabric",
        "class": "capability",
        "mode": "derived",
    },
    "health": {
        "owner": "living-fabric",
        "class": "assurance",
        "mode": "derived",
    },
    "freshness": {
        "owner": "living-fabric",
        "class": "temporal",
        "mode": "derived",
    },
    "staleness": {
        "owner": "living-fabric",
        "class": "temporal",
        "mode": "derived",
    },
    "change": {
        "owner": "living-fabric",
        "class": "temporal",
        "mode": "derived",
    },
    "history": {
        "owner": "living-fabric",
        "class": "temporal",
        "mode": "derived",
    },
    "receipts": {
        "owner": "living-fabric",
        "class": "assurance",
        "mode": "derived",
    },
    "source_integrity": {
        "owner": "living-fabric",
        "class": "assurance",
        "mode": "derived",
    },
    "projection_integrity": {
        "owner": "living-fabric",
        "class": "assurance",
        "mode": "derived",
    },
    "replay": {
        "owner": "living-fabric",
        "class": "temporal",
        "mode": "derived",
    },
    "readiness": {
        "owner": "living-fabric",
        "class": "assurance",
        "mode": "derived",
    },
}


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
    material = compact_json(
        value
    ).encode(
        "utf-8"
    )

    try:
        import blake3

        return blake3.blake3(
            material
        ).hexdigest()

    except ImportError:
        return hashlib.sha256(
            material
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
    fabric_root.mkdir(
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


def source_state(
    path: Path,
) -> dict[str, Any]:
    try:
        info = path.stat()

    except OSError:
        return {
            "path":
                str(
                    path
                ),
            "present":
                False,
            "mtime_ns":
                None,
            "size":
                None,
        }

    return {
        "path":
            str(
                path
            ),
        "present":
            path.is_file(),
        "mtime_ns":
            info.st_mtime_ns,
        "size":
            info.st_size,
    }


def freshness(
    mtime_ns: int | None,
) -> dict[str, Any]:
    if not mtime_ns:
        return {
            "state":
                "absent",
            "age_seconds":
                None,
        }

    age = max(
        0.0,
        (
            time.time_ns()
            - mtime_ns
        )
        / 1_000_000_000,
    )

    if age <= 30:
        state = "hot"

    elif age <= 300:
        state = "current"

    elif age <= 3600:
        state = "aging"

    else:
        state = "stale"

    return {
        "state":
            state,
        "age_seconds":
            age,
    }


def governance_records(
    snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
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


def reverse_dependencies(
    records: list[dict[str, Any]],
) -> dict[str, list[str]]:
    result: dict[
        str,
        set[str],
    ] = {}

    for record in records:
        record_id = record.get(
            "id"
        )

        dependencies = record.get(
            "dependencies",
            []
        )

        if not record_id:
            continue

        if not isinstance(
            dependencies,
            list,
        ):
            continue

        for dependency in dependencies:
            dependency_id = str(
                dependency
            )

            result.setdefault(
                dependency_id,
                set(),
            ).add(
                str(
                    record_id
                )
            )

    return {
        key:
            sorted(
                values
            )
        for key, values
        in sorted(
            result.items()
        )
    }


def authority_projection(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    counts: dict[str, int] = {}

    for record in records:
        authority = str(
            record.get(
                "authority",
                "unknown",
            )
        )

        counts[
            authority
        ] = (
            counts.get(
                authority,
                0,
            )
            + 1
        )

    return {
        "record_count":
            len(
                records
            ),
        "authority_counts":
            dict(
                sorted(
                    counts.items()
                )
            ),
        "digest":
            stable_hash(
                counts
            ),
    }


def supersession_projection(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    edges = []

    for record in records:
        supersedes = record.get(
            "supersedes"
        )

        if not supersedes:
            continue

        if isinstance(
            supersedes,
            list,
        ):
            targets = supersedes

        else:
            targets = [
                supersedes
            ]

        for target in targets:
            edges.append(
                {
                    "from":
                        record.get(
                            "id"
                        ),
                    "to":
                        target,
                }
            )

    edges = sorted(
        edges,
        key=lambda item:
            (
                str(
                    item.get(
                        "from"
                    )
                ),
                str(
                    item.get(
                        "to"
                    )
                ),
            ),
    )

    return {
        "edge_count":
            len(
                edges
            ),
        "edges":
            edges,
        "digest":
            stable_hash(
                edges
            ),
    }


def lineage_projection(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    lineage = []

    for record in records:
        lineage.append(
            {
                "id":
                    record.get(
                        "id"
                    ),
                "stream":
                    record.get(
                        "stream"
                    ),
                "version":
                    record.get(
                        "version"
                    ),
                "authority":
                    record.get(
                        "authority"
                    ),
                "supersedes":
                    record.get(
                        "supersedes"
                    ),
                "dependencies":
                    record.get(
                        "dependencies",
                        [],
                    ),
                "relationships":
                    record.get(
                        "relationships",
                        [],
                    ),
                "provenance":
                    record.get(
                        "provenance"
                    ),
            }
        )

    lineage = sorted(
        lineage,
        key=lambda item:
            (
                str(
                    item.get(
                        "stream"
                    )
                ),
                str(
                    item.get(
                        "id"
                    )
                ),
            ),
    )

    return {
        "record_count":
            len(
                lineage
            ),
        "records":
            lineage,
        "digest":
            stable_hash(
                lineage
            ),
    }


def derive_runtime_surfaces(
    living_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "filesystem":
            living_state.get(
                "filesystem",
                {},
            ),
        "services":
            living_state.get(
                "services",
                [],
            ),
        "processes":
            living_state.get(
                "processes",
                [],
            ),
        "network":
            living_state.get(
                "listening_tcp",
                [],
            ),
        "system":
            living_state.get(
                "system",
                {},
            ),
        "packages":
            living_state.get(
                "packages",
                [],
            ),
        "git":
            living_state.get(
                "git"
            ),
        "datastores":
            living_state.get(
                "sqlite",
                [],
            ),
        "environment":
            living_state.get(
                "environment",
                {},
            ),
    }


def derive_persona_surfaces(
    extensions: dict[str, Any],
) -> dict[str, Any]:
    extension_surfaces = extensions.get(
        "surfaces",
        {}
    )

    if not isinstance(
        extension_surfaces,
        dict,
    ):
        extension_surfaces = {}

    persona = extension_surfaces.get(
        "persona",
        {}
    )

    if not isinstance(
        persona,
        dict,
    ):
        persona = {}

    runtime = persona.get(
        "runtime",
        {}
    )

    if not isinstance(
        runtime,
        dict,
    ):
        runtime = {}

    components = runtime.get(
        "components",
        {}
    )

    if not isinstance(
        components,
        dict,
    ):
        components = {}

    return {
        "persona":
            persona,
        "persona_traits":
            extension_surfaces.get(
                "persona_traits",
                {},
            ),
        "persona_trait_state":
            components.get(
                "trait_state",
                {},
            ),
        "persona_trait_history":
            components.get(
                "trait_history",
                {},
            ),
        "persona_trait_candidates":
            components.get(
                "trait_candidate_persistence",
                {},
            ),
        "persona_trait_evidence":
            components.get(
                "trait_evidence",
                {},
            ),
        "persona_trait_evaluation":
            components.get(
                "trait_evaluation",
                {},
            ),
        "persona_trait_adjudication":
            components.get(
                "trait_adjudication",
                {},
            ),
        "persona_trait_experiment":
            components.get(
                "trait_experiment",
                {},
            ),
    }


def surface_envelope(
    name: str,
    substance: Any,
) -> dict[str, Any]:
    specification = surface_catalog[
        name
    ]

    return {
        "schema":
            "savant.living-surface.v1",
        "id":
            f"living:{name}",
        "name":
            name,
        "owner":
            specification[
                "owner"
            ],
        "class":
            specification[
                "class"
            ],
        "mode":
            specification[
                "mode"
            ],
        "projection_only":
            True,
        "authority_effect":
            "none",
        "filesystem_presence_establishes_authority":
            False,
        "substance":
            substance,
        "digest":
            stable_hash(
                substance
            ),
    }


def build_fabric() -> dict[str, Any]:
    previous = read_json(
        current_path
    )

    base = read_json(
        base_projection_path
    )

    extensions = read_json(
        extension_projection_path
    )

    living_state = read_json(
        living_state_path
    )

    living_health = read_json(
        living_state_health_path
    )

    governance_status = read_json(
        governance_status_path
    )

    governance_snapshot = read_json(
        governance_snapshot_path
    )

    governance_graph = read_json(
        governance_graph_path
    )

    records = governance_records(
        governance_snapshot
    )

    base_surfaces = base.get(
        "surfaces",
        {}
    )

    if not isinstance(
        base_surfaces,
        dict,
    ):
        base_surfaces = {}

    extension_surfaces = extensions.get(
        "surfaces",
        {}
    )

    if not isinstance(
        extension_surfaces,
        dict,
    ):
        extension_surfaces = {}

    substances: dict[
        str,
        Any,
    ] = {}

    for name in (
        "canon",
        "structure",
        "masterplan",
        "terminology",
        "rules",
        "decisions",
        "permissions",
        "invariants",
        "compatibility",
        "risks",
        "enhancements",
        "unknowns",
        "dependencies",
        "provenance",
        "assurance",
        "implementation",
        "evidence",
        "evolution",
        "context",
    ):
        substances[
            name
        ] = base_surfaces.get(
            name,
            {},
        )

    substances[
        "sdump"
    ] = extension_surfaces.get(
        "sdump",
        {},
    )

    substances.update(
        derive_persona_surfaces(
            extensions
        )
    )

    substances.update(
        derive_runtime_surfaces(
            living_state
        )
    )

    substances[
        "dependents"
    ] = reverse_dependencies(
        records
    )

    substances[
        "authority"
    ] = authority_projection(
        records
    )

    substances[
        "conflicts"
    ] = {
        "count":
            governance_status.get(
                "conflict_count",
                0,
            ),
        "records":
            governance_snapshot.get(
                "conflicts",
                [],
            ),
    }

    substances[
        "supersession"
    ] = supersession_projection(
        records
    )

    substances[
        "lineage"
    ] = lineage_projection(
        records
    )

    source_paths = (
        base_projection_path,
        extension_projection_path,
        living_state_path,
        living_state_health_path,
        governance_status_path,
        governance_snapshot_path,
        governance_graph_path,
    )

    sources = {
        path.name
        + ":"
        + stable_hash(
            str(
                path
            )
        )[:12]:
            source_state(
                path
            )
        for path
        in source_paths
    }

    source_freshness = {
        key:
            freshness(
                value.get(
                    "mtime_ns"
                )
            )
        for key, value
        in sources.items()
    }

    capabilities = {
        "atomic_publication":
            True,
        "append_only_history":
            True,
        "projection_receipts":
            True,
        "deterministic_projection":
            True,
        "content_addressed_surfaces":
            True,
        "surface_level_hashing":
            True,
        "whole_fabric_hashing":
            True,
        "incremental_change_detection":
            True,
        "selective_surface_change_detection":
            True,
        "dependency_projection":
            True,
        "reverse_dependency_projection":
            True,
        "provenance_projection":
            True,
        "lineage_projection":
            True,
        "supersession_projection":
            True,
        "authority_projection":
            True,
        "conflict_projection":
            True,
        "freshness_tracking":
            True,
        "staleness_detection":
            True,
        "temporal_sequence":
            True,
        "deterministic_replay_material":
            True,
        "last_known_good_retention":
            True,
        "failure_isolation":
            True,
        "source_integrity_projection":
            True,
        "projection_integrity_projection":
            True,
        "health_projection":
            True,
        "readiness_projection":
            True,
        "capability_discovery":
            True,
        "persona_layer_projection":
            True,
        "living_sdump_projection":
            True,
        "governance_stream_projection":
            True,
        "runtime_state_projection":
            True,
        "implementation_projection":
            True,
        "evidence_projection":
            True,
        "evolution_projection":
            True,
        "context_projection":
            True,
        "secret_values_serialized":
            False,
        "authority_mutation":
            False,
        "source_mutation":
            False,
        "duplicate_authority":
            False,
        "filesystem_authority_inference":
            False,
        "orjson":
            module_available(
                "orjson"
            ),
        "blake3":
            module_available(
                "blake3"
            ),
        "watchfiles":
            module_available(
                "watchfiles"
            ),
    }

    substances[
        "capabilities"
    ] = capabilities

    substances[
        "freshness"
    ] = source_freshness

    substances[
        "staleness"
    ] = {
        key:
            value
        for key, value
        in source_freshness.items()
        if value.get(
            "state"
        ) in {
            "aging",
            "stale",
            "absent",
        }
    }

    previous_surface_digests = previous.get(
        "surface_digests",
        {}
    )

    if not isinstance(
        previous_surface_digests,
        dict,
    ):
        previous_surface_digests = {}

    preliminary_digests = {
        name:
            stable_hash(
                substance
            )
        for name, substance
        in substances.items()
    }

    changed_before_meta = sorted(
        name
        for name, digest
        in preliminary_digests.items()
        if previous_surface_digests.get(
            name
        ) != digest
    )

    substances[
        "change"
    ] = {
        "changed_surfaces":
            changed_before_meta,
        "change_count":
            len(
                changed_before_meta
            ),
        "source_sequences": {
            "living_state":
                living_state.get(
                    "sequence"
                ),
            "living_projection":
                base.get(
                    "sequence"
                ),
            "living_extensions":
                extensions.get(
                    "sequence"
                ),
        },
    }

    substances[
        "history"
    ] = {
        "history_path":
            str(
                history_path
            ),
        "previous_fabric_hash":
            previous.get(
                "fabric_hash"
            ),
        "previous_sequence":
            previous.get(
                "sequence"
            ),
    }

    substances[
        "source_integrity"
    ] = {
        "sources":
            sources,
        "all_required_present":
            all(
                state.get(
                    "present",
                    False,
                )
                for state
                in sources.values()
            ),
        "source_digest":
            stable_hash(
                sources
            ),
    }

    substances[
        "projection_integrity"
    ] = {
        "base_projection_present":
            bool(
                base
            ),
        "extension_projection_present":
            bool(
                extensions
            ),
        "living_state_present":
            bool(
                living_state
            ),
        "governance_present":
            bool(
                governance_status
            ),
        "base_projection_hash":
            base.get(
                "projection_hash"
            ),
        "extension_projection_hash":
            extensions.get(
                "projection_hash"
            ),
        "living_state_hash":
            living_state.get(
                "snapshot_hash"
            ),
        "governance_digest":
            governance_status.get(
                "digest"
            ),
    }

    substances[
        "replay"
    ] = {
        "source_digest":
            stable_hash(
                sources
            ),
        "catalog_digest":
            stable_hash(
                surface_catalog
            ),
        "deterministic_inputs": [
            str(
                path
            )
            for path
            in source_paths
        ],
    }

    substances[
        "health"
    ] = {
        "living_state_healthy":
            living_health.get(
                "healthy",
                False,
            ),
        "governance_conflict_count":
            governance_status.get(
                "conflict_count",
                0,
            ),
        "required_sources_present":
            all(
                state.get(
                    "present",
                    False,
                )
                for state
                in sources.values()
            ),
    }

    substances[
        "readiness"
    ] = {
        "ready":
            bool(
                living_health.get(
                    "healthy",
                    False,
                )
            )
            and bool(
                base
            )
            and bool(
                extensions
            )
            and bool(
                governance_status
            )
            and (
                governance_status.get(
                    "conflict_count",
                    0,
                )
                == 0
            ),
        "living_state_healthy":
            living_health.get(
                "healthy",
                False,
            ),
        "governance_conflict_count":
            governance_status.get(
                "conflict_count",
                0,
            ),
    }

    surfaces = {
        name:
            surface_envelope(
                name,
                substances.get(
                    name,
                    {},
                ),
            )
        for name
        in sorted(
            surface_catalog
        )
    }

    surface_digests = {
        name:
            surface[
                "digest"
            ]
        for name, surface
        in surfaces.items()
    }

    changed_surfaces = sorted(
        name
        for name, digest
        in surface_digests.items()
        if previous_surface_digests.get(
            name
        ) != digest
    )

    unchanged_surfaces = sorted(
        name
        for name, digest
        in surface_digests.items()
        if previous_surface_digests.get(
            name
        ) == digest
    )

    try:
        sequence = (
            int(
                previous.get(
                    "sequence",
                    0,
                )
            )
            + 1
        )

    except (
        TypeError,
        ValueError,
    ):
        sequence = 1

    fabric = {
        "schema":
            schema,
        "id":
            "savant:living-fabric",
        "sequence":
            sequence,
        "generated_at_unix_ns":
            time.time_ns(),
        "projection_only":
            True,
        "authority_effect":
            "none",
        "source_authority_preserved":
            True,
        "filesystem_presence_establishes_authority":
            False,
        "single_fabric":
            True,
        "surface_count":
            len(
                surfaces
            ),
        "catalog":
            surface_catalog,
        "catalog_digest":
            stable_hash(
                surface_catalog
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
        "sources":
            sources,
        "capabilities":
            capabilities,
        "previous_fabric_hash":
            previous.get(
                "fabric_hash"
            ),
    }

    fabric[
        "fabric_hash"
    ] = stable_hash(
        {
            key:
                value
            for key, value
            in fabric.items()
            if key != "fabric_hash"
        }
    )

    return fabric


def persist_fabric() -> dict[str, Any]:
    started = time.monotonic()

    try:
        fabric = build_fabric()

        previous = read_json(
            current_path
        )

        materially_changed = (
            not previous
            or previous.get(
                "surface_digests"
            )
            != fabric.get(
                "surface_digests"
            )
        )

        if materially_changed:
            atomic_write_json(
                current_path,
                fabric,
            )

            event = {
                "schema":
                    "savant.living-fabric.event.v1",
                "sequence":
                    fabric[
                        "sequence"
                    ],
                "generated_at_unix_ns":
                    fabric[
                        "generated_at_unix_ns"
                    ],
                "fabric_hash":
                    fabric[
                        "fabric_hash"
                    ],
                "previous_fabric_hash":
                    fabric.get(
                        "previous_fabric_hash"
                    ),
                "changed_surfaces":
                    fabric[
                        "changed_surfaces"
                    ],
                "change_count":
                    fabric[
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

            atomic_write_json(
                receipt_path,
                {
                    "schema":
                        "savant.living-fabric.receipt.v1",
                    "sequence":
                        fabric[
                            "sequence"
                        ],
                    "fabric_hash":
                        fabric[
                            "fabric_hash"
                        ],
                    "event_hash":
                        event[
                            "event_hash"
                        ],
                    "changed_surfaces":
                        fabric[
                            "changed_surfaces"
                        ],
                    "published":
                        True,
                    "authority_effect":
                        "none",
                    "published_at_unix_ns":
                        time.time_ns(),
                },
            )

        health = {
            "schema":
                "savant.living-fabric.health.v1",
            "healthy":
                True,
            "materially_changed":
                materially_changed,
            "sequence":
                (
                    fabric[
                        "sequence"
                    ]
                    if materially_changed
                    else previous.get(
                        "sequence"
                    )
                ),
            "fabric_hash":
                (
                    fabric[
                        "fabric_hash"
                    ]
                    if materially_changed
                    else previous.get(
                        "fabric_hash"
                    )
                ),
            "surface_count":
                fabric[
                    "surface_count"
                ],
            "change_count":
                (
                    fabric[
                        "change_count"
                    ]
                    if materially_changed
                    else 0
                ),
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

        return (
            fabric
            if materially_changed
            else previous
        )

    except Exception as error:
        atomic_write_json(
            health_path,
            {
                "schema":
                    "savant.living-fabric.health.v1",
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


def module_available(
    name: str,
) -> bool:
    try:
        __import__(
            name
        )

        return True

    except ImportError:
        return False


def source_signature() -> str:
    states = [
        source_state(
            path
        )
        for path
        in (
            base_projection_path,
            extension_projection_path,
            living_state_path,
            living_state_health_path,
            governance_status_path,
            governance_snapshot_path,
            governance_graph_path,
        )
    ]

    return stable_hash(
        states
    )


def event_loop(
    interval: float,
) -> None:
    persist_fabric()

    previous_signature = source_signature()

    while not stop_event.wait(
        interval
    ):
        current_signature = source_signature()

        if (
            current_signature
            == previous_signature
        ):
            continue

        persist_fabric()

        previous_signature = current_signature


def signal_handler(
    signum: int,
    frame: Any,
) -> None:
    del signum
    del frame

    stop_event.set()


def one_shot() -> int:
    fabric = persist_fabric()

    print(
        compact_json(
            {
                "ok":
                    True,
                "sequence":
                    fabric.get(
                        "sequence"
                    ),
                "fabric_hash":
                    fabric.get(
                        "fabric_hash"
                    ),
                "surface_count":
                    fabric.get(
                        "surface_count"
                    ),
                "changed_surfaces":
                    fabric.get(
                        "changed_surfaces",
                        [],
                    ),
                "current":
                    str(
                        current_path
                    ),
            }
        )
    )

    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="savant-living-fabric",
    )

    value.add_argument(
        "--once",
        action="store_true",
    )

    value.add_argument(
        "--interval",
        type=float,
        default=2.0,
    )

    return value


def main() -> int:
    arguments = parser().parse_args()

    fabric_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    signal.signal(
        signal.SIGTERM,
        signal_handler,
    )

    signal.signal(
        signal.SIGINT,
        signal_handler,
    )

    if arguments.once:
        return one_shot()

    event_loop(
        interval=max(
            1.0,
            arguments.interval,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
