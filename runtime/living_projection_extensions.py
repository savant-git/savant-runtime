#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any


schema = "savant.living-projection.extensions.v1"

runtime_root = Path(
    "/root/savant-runtime"
).resolve()

projection_root = (
    runtime_root
    / "runtime"
    / "living-projection"
).resolve()

current_path = (
    projection_root
    / "extensions.json"
)

health_path = (
    projection_root
    / "extensions-health.json"
)

history_path = (
    projection_root
    / "extensions-history.jsonl"
)

envoy_root = (
    runtime_root
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "envoy"
).resolve()

envoy_runtime_root = (
    envoy_root
    / "runtime"
)

envoy_trait_registry_root = (
    envoy_root
    / "registry"
    / "traits"
)

persona_sources = (
    envoy_runtime_root
    / "persona_engine.py",
    envoy_runtime_root
    / "trait_state.py",
    envoy_runtime_root
    / "trait_history.py",
    envoy_runtime_root
    / "trait_persistence.py",
    envoy_runtime_root
    / "trait_candidate_persistence.py",
    envoy_runtime_root
    / "trait_evidence.py",
    envoy_runtime_root
    / "trait_evaluation.py",
    envoy_runtime_root
    / "trait_adjudication.py",
    envoy_runtime_root
    / "trait_experiment.py",
)

living_state_path = (
    runtime_root
    / "runtime"
    / "living-state"
    / "current.json"
)

sdump_source_root = (
    runtime_root
    / "source"
)

sdump_runtime_candidates = (
    runtime_root
    / "runtime"
    / "sdump",
    runtime_root
    / "runtime"
    / "living-sdump",
    runtime_root
    / "tools"
    / "sdump-enterprise",
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


def sha256_file(
    path: Path,
) -> str | None:
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

    except OSError:
        return None

    return digest.hexdigest()


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
    projection_root.mkdir(
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


def freshness(
    mtime_ns: int | None,
) -> dict[str, Any]:
    if not mtime_ns:
        return {
            "state": "absent",
            "age_seconds": None,
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
        "state": state,
        "age_seconds": age,
    }


def file_state(
    path: Path,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path":
            str(
                path
            ),
        "present":
            False,
        "authority_effect":
            "none",
    }

    try:
        info = path.stat()

    except OSError:
        record[
            "freshness"
        ] = freshness(
            None
        )

        return record

    record.update(
        {
            "present":
                path.is_file(),
            "size":
                info.st_size,
            "mtime_ns":
                info.st_mtime_ns,
            "sha256":
                (
                    sha256_file(
                        path
                    )
                    if path.is_file()
                    else None
                ),
            "freshness":
                freshness(
                    info.st_mtime_ns
                ),
        }
    )

    return record


def directory_state(
    path: Path,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path":
            str(
                path
            ),
        "present":
            path.is_dir(),
        "file_count":
            0,
        "directory_count":
            0,
        "bytes":
            0,
        "newest_mtime_ns":
            None,
        "authority_effect":
            "none",
    }

    if not path.is_dir():
        record[
            "freshness"
        ] = freshness(
            None
        )

        return record

    newest = 0

    try:
        for root, directories, filenames in os.walk(
            path
        ):
            directories[:] = [
                name
                for name
                in directories
                if name != "__pycache__"
            ]

            record[
                "directory_count"
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
                    "file_count"
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

    record[
        "freshness"
    ] = freshness(
        record[
            "newest_mtime_ns"
        ]
    )

    return record


def json_shape(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        dict,
    ):
        return {
            "type":
                "object",
            "keys":
                sorted(
                    str(
                        key
                    )
                    for key
                    in value
                ),
            "count":
                len(
                    value
                ),
        }

    if isinstance(
        value,
        list,
    ):
        return {
            "type":
                "array",
            "count":
                len(
                    value
                ),
        }

    return {
        "type":
            type(
                value
            ).__name__,
    }


def trait_registry_projection() -> dict[str, Any]:
    files: list[
        dict[str, Any]
    ] = []

    trait_documents: list[
        dict[str, Any]
    ] = []

    if envoy_trait_registry_root.is_dir():
        for path in sorted(
            envoy_trait_registry_root.rglob(
                "*.json"
            ),
            key=lambda item:
                str(
                    item
                ).casefold(),
        ):
            state = file_state(
                path
            )

            files.append(
                state
            )

            try:
                value = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )

                trait_documents.append(
                    {
                        "path":
                            str(
                                path
                            ),
                        "shape":
                            json_shape(
                                value
                            ),
                        "digest":
                            stable_hash(
                                value
                            ),
                    }
                )

            except (
                OSError,
                json.JSONDecodeError,
            ):
                trait_documents.append(
                    {
                        "path":
                            str(
                                path
                            ),
                        "shape": {
                            "type":
                                "unreadable",
                        },
                        "digest":
                            None,
                    }
                )

    return {
        "schema":
            "savant.living-persona-trait-registry.v1",
        "owner":
            "envoy",
        "projection_only":
            True,
        "authority_effect":
            "none",
        "registry_root":
            str(
                envoy_trait_registry_root
            ),
        "file_count":
            len(
                files
            ),
        "files":
            files,
        "documents":
            trait_documents,
        "digest":
            stable_hash(
                trait_documents
            ),
    }


def persona_runtime_projection() -> dict[str, Any]:
    components = {
        path.stem:
            file_state(
                path
            )
        for path
        in persona_sources
    }

    present = sorted(
        name
        for name, state
        in components.items()
        if state.get(
            "present"
        )
    )

    absent = sorted(
        name
        for name, state
        in components.items()
        if not state.get(
            "present"
        )
    )

    capabilities = {
        "persona_engine":
            components.get(
                "persona_engine",
                {}
            ).get(
                "present",
                False,
            ),
        "trait_state":
            components.get(
                "trait_state",
                {}
            ).get(
                "present",
                False,
            ),
        "trait_history":
            components.get(
                "trait_history",
                {}
            ).get(
                "present",
                False,
            ),
        "trait_persistence":
            components.get(
                "trait_persistence",
                {}
            ).get(
                "present",
                False,
            ),
        "candidate_persistence":
            components.get(
                "trait_candidate_persistence",
                {}
            ).get(
                "present",
                False,
            ),
        "evidence":
            components.get(
                "trait_evidence",
                {}
            ).get(
                "present",
                False,
            ),
        "evaluation":
            components.get(
                "trait_evaluation",
                {}
            ).get(
                "present",
                False,
            ),
        "adjudication":
            components.get(
                "trait_adjudication",
                {}
            ).get(
                "present",
                False,
            ),
        "experiment":
            components.get(
                "trait_experiment",
                {}
            ).get(
                "present",
                False,
            ),
    }

    return {
        "schema":
            "savant.living-persona-runtime.v1",
        "owner":
            "envoy",
        "projection_only":
            True,
        "authority_effect":
            "none",
        "runtime_root":
            str(
                envoy_runtime_root
            ),
        "components":
            components,
        "present_components":
            present,
        "absent_components":
            absent,
        "capabilities":
            capabilities,
        "digest":
            stable_hash(
                components
            ),
    }


def persona_projection() -> dict[str, Any]:
    runtime = persona_runtime_projection()
    registry = trait_registry_projection()

    layer_digests = {
        "runtime":
            runtime[
                "digest"
            ],
        "trait_registry":
            registry[
                "digest"
            ],
    }

    return {
        "schema":
            "savant.living-persona.v1",
        "id":
            "living:persona",
        "owner":
            "envoy",
        "projection_only":
            True,
        "authority_effect":
            "none",
        "filesystem_presence_establishes_authority":
            False,
        "source_authority_preserved":
            True,
        "duplicate_persona_state_created":
            False,
        "runtime":
            runtime,
        "trait_registry":
            registry,
        "layers": {
            "persona_engine": {
                "owner":
                    "envoy",
                "source":
                    str(
                        envoy_runtime_root
                        / "persona_engine.py"
                    ),
                "projection_only":
                    True,
            },
            "trait_state": {
                "owner":
                    "envoy",
                "source":
                    str(
                        envoy_runtime_root
                        / "trait_state.py"
                    ),
                "projection_only":
                    True,
            },
            "trait_history": {
                "owner":
                    "envoy",
                "source":
                    str(
                        envoy_runtime_root
                        / "trait_history.py"
                    ),
                "projection_only":
                    True,
            },
            "trait_registry": {
                "owner":
                    "envoy",
                "source":
                    str(
                        envoy_trait_registry_root
                    ),
                "projection_only":
                    True,
            },
            "trait_persistence": {
                "owner":
                    "envoy",
                "source":
                    str(
                        envoy_runtime_root
                        / "trait_persistence.py"
                    ),
                "projection_only":
                    True,
            },
            "trait_candidates": {
                "owner":
                    "envoy",
                "source":
                    str(
                        envoy_runtime_root
                        / "trait_candidate_persistence.py"
                    ),
                "projection_only":
                    True,
            },
            "trait_evidence": {
                "owner":
                    "envoy",
                "source":
                    str(
                        envoy_runtime_root
                        / "trait_evidence.py"
                    ),
                "projection_only":
                    True,
            },
            "trait_evaluation": {
                "owner":
                    "envoy",
                "source":
                    str(
                        envoy_runtime_root
                        / "trait_evaluation.py"
                    ),
                "projection_only":
                    True,
            },
            "trait_adjudication": {
                "owner":
                    "envoy",
                "source":
                    str(
                        envoy_runtime_root
                        / "trait_adjudication.py"
                    ),
                "projection_only":
                    True,
            },
            "trait_experiment": {
                "owner":
                    "envoy",
                "source":
                    str(
                        envoy_runtime_root
                        / "trait_experiment.py"
                    ),
                "projection_only":
                    True,
            },
        },
        "layer_digests":
            layer_digests,
        "digest":
            stable_hash(
                layer_digests
            ),
    }


def latest_sdump_from_living_state() -> dict[str, Any] | None:
    living_state = read_json(
        living_state_path
    )

    value = living_state.get(
        "latest_sdump"
    )

    if isinstance(
        value,
        dict,
    ):
        return value

    return None


def discover_latest_sdump() -> dict[str, Any] | None:
    if not sdump_source_root.is_dir():
        return None

    candidates: list[
        Path
    ] = []

    try:
        candidates = [
            path
            for path
            in sdump_source_root.rglob(
                "sdump_*.txt"
            )
            if path.is_file()
        ]

    except OSError:
        return None

    if not candidates:
        return None

    try:
        latest = max(
            candidates,
            key=lambda path:
                path.stat().st_mtime_ns,
        )

        info = latest.stat()

    except OSError:
        return None

    return {
        "path":
            str(
                latest
            ),
        "size":
            info.st_size,
        "mtime_ns":
            info.st_mtime_ns,
        "sha256":
            sha256_file(
                latest
            ),
    }


def sdump_projection() -> dict[str, Any]:
    observed = (
        latest_sdump_from_living_state()
        or discover_latest_sdump()
    )

    runtime_surfaces = [
        directory_state(
            path
        )
        for path
        in sdump_runtime_candidates
    ]

    latest_mtime_ns = None

    if isinstance(
        observed,
        dict,
    ):
        raw_mtime = observed.get(
            "mtime_ns"
        )

        if isinstance(
            raw_mtime,
            int,
        ):
            latest_mtime_ns = raw_mtime

    return {
        "schema":
            "savant.living-sdump-projection.v1",
        "id":
            "living:sdump",
        "owner":
            "existing-living-sdump",
        "projection_only":
            True,
        "authority_effect":
            "none",
        "filesystem_presence_establishes_authority":
            False,
        "existing_implementation_preserved":
            True,
        "mutation_enabled":
            False,
        "duplicate_sdump_authority_created":
            False,
        "latest":
            observed,
        "freshness":
            freshness(
                latest_mtime_ns
            ),
        "runtime_surfaces":
            runtime_surfaces,
        "digest":
            stable_hash(
                {
                    "latest":
                        observed,
                    "runtime_surfaces":
                        runtime_surfaces,
                }
            ),
    }


def build_projection() -> dict[str, Any]:
    previous = read_json(
        current_path
    )

    persona = persona_projection()
    sdump = sdump_projection()

    surfaces = {
        "persona":
            persona,
        "persona_traits":
            persona[
                "trait_registry"
            ],
        "sdump":
            sdump,
    }

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

    changed = sorted(
        name
        for name, digest
        in surface_digests.items()
        if previous_digests.get(
            name
        ) != digest
    )

    unchanged = sorted(
        name
        for name, digest
        in surface_digests.items()
        if previous_digests.get(
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

    projection = {
        "schema":
            schema,
        "sequence":
            sequence,
        "generated_at_unix_ns":
            time.time_ns(),
        "projection_only":
            True,
        "authority_effect":
            "none",
        "filesystem_presence_establishes_authority":
            False,
        "source_authority_preserved":
            True,
        "surfaces":
            surfaces,
        "surface_count":
            len(
                surfaces
            ),
        "surface_digests":
            surface_digests,
        "changed_surfaces":
            changed,
        "unchanged_surfaces":
            unchanged,
        "change_count":
            len(
                changed
            ),
        "capabilities": {
            "living_sdump_observation":
                True,
            "living_sdump_mutation":
                False,
            "living_persona_projection":
                True,
            "living_trait_registry_projection":
                True,
            "persona_runtime_discovery":
                True,
            "trait_capability_discovery":
                True,
            "trait_history_visibility":
                True,
            "trait_persistence_visibility":
                True,
            "trait_candidate_visibility":
                True,
            "trait_evidence_visibility":
                True,
            "trait_evaluation_visibility":
                True,
            "trait_adjudication_visibility":
                True,
            "trait_experiment_visibility":
                True,
            "source_hashing":
                True,
            "freshness_tracking":
                True,
            "incremental_surface_diff":
                True,
            "atomic_publication":
                True,
            "projection_history":
                True,
            "owner_preservation":
                True,
            "duplicate_authority":
                False,
            "historical_backup_projection":
                False,
            "secret_values_serialized":
                False,
        },
    }

    projection[
        "previous_projection_hash"
    ] = previous.get(
        "projection_hash"
    )

    projection[
        "projection_hash"
    ] = stable_hash(
        {
            key:
                value
            for key, value
            in projection.items()
            if key != "projection_hash"
        }
    )

    return projection


def persist_projection() -> dict[str, Any]:
    started = time.monotonic()

    try:
        projection = build_projection()

        atomic_write_json(
            current_path,
            projection,
        )

        event = {
            "schema":
                "savant.living-projection.extensions.event.v1",
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

        atomic_write_json(
            health_path,
            {
                "schema":
                    "savant.living-projection.extensions.health.v1",
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
            },
        )

        return projection

    except Exception as error:
        atomic_write_json(
            health_path,
            {
                "schema":
                    "savant.living-projection.extensions.health.v1",
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


def main() -> int:
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
                        current_path
                    ),
            }
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
