#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


savant_root = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

authority_root = (
    savant_root
    / "canon-system"
    / "authority"
    / "living"
)

projection_root = (
    savant_root
    / "canon-system"
    / "projections"
    / "living"
)

bootstrap_path = (
    authority_root
    / "bootstrap.json"
)

ledger_path = (
    authority_root
    / "ledger.jsonl"
)

snapshot_path = (
    projection_root
    / "snapshot.json"
)

graph_path = (
    projection_root
    / "graph.json"
)

status_path = (
    projection_root
    / "status.json"
)


schema = (
    "savant.living-governance.v1"
)


authority_order = {
    "current_user_directive":
        0,

    "accepted_authoritative_graph":
        1,

    "accepted_decision":
        2,

    "constitutional_canon":
        3,

    "verified_implementation":
        4,

    "admitted_evidence":
        5,

    "deterministic_projection":
        6,

    "historical_implementation":
        7,

    "historical_document":
        8,

    "inference":
        9,

    "speculation":
        10,
}


class living_governance_error(
    RuntimeError
):
    pass


def utc_now() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode(
            "utf-8"
        )
    ).hexdigest()


def read_json(
    path: Path,
) -> Any:
    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except FileNotFoundError as exc:
        raise living_governance_error(
            f"missing required file: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise living_governance_error(
            f"invalid json: {path}: {exc}"
        ) from exc


def atomic_write(
    path: Path,
    text: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary = (
        tempfile.mkstemp(
            prefix=(
                "."
                + path.name
                + "."
            ),
            dir=str(
                path.parent
            ),
            text=True,
        )
    )

    temp_path = Path(
        temporary
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                text
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temp_path,
            path,
        )
    finally:
        if temp_path.exists():
            temp_path.unlink()


def normalize_dependencies(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        value = [
            value
        ]

    if not isinstance(
        value,
        list,
    ):
        raise living_governance_error(
            "dependencies must be a list"
        )

    return sorted(
        {
            str(
                item
            ).strip()
            for item in value
            if str(
                item
            ).strip()
        }
    )


def normalize_relationships(
    value: Any,
) -> list[dict[str, str]]:
    if value is None:
        return []

    if not isinstance(
        value,
        list,
    ):
        raise living_governance_error(
            "relationships must be a list"
        )

    normalized:
        list[
            dict[
                str,
                str,
            ]
        ] = []

    for item in value:
        if not isinstance(
            item,
            dict,
        ):
            raise living_governance_error(
                "relationship must be an object"
            )

        kind = str(
            item.get(
                "kind",
                "",
            )
        ).strip()

        target = str(
            item.get(
                "target",
                "",
            )
        ).strip()

        if (
            not kind
            or not target
        ):
            raise living_governance_error(
                (
                    "relationship requires "
                    "kind and target"
                )
            )

        normalized.append(
            {
                "kind":
                    kind,

                "target":
                    target,
            }
        )

    return sorted(
        normalized,
        key=lambda item: (
            item[
                "kind"
            ],
            item[
                "target"
            ],
        ),
    )


def normalize_record(
    value: dict[str, Any],
    *,
    stream: str,
    default_authority: str,
    default_provenance: dict[str, Any],
) -> dict[str, Any]:
    semantic_id = str(
        value.get(
            "id",
            "",
        )
    ).strip()

    if not semantic_id:
        raise living_governance_error(
            "record id is required"
        )

    text = str(
        value.get(
            "text",
            "",
        )
    ).strip()

    if not text:
        raise living_governance_error(
            (
                "record text is required: "
                + semantic_id
            )
        )

    authority = str(
        value.get(
            "authority",
            default_authority,
        )
    ).strip()

    if (
        authority
        not in authority_order
    ):
        raise living_governance_error(
            (
                "unknown authority class: "
                + authority
            )
        )

    priority = int(
        value.get(
            "priority",
            1000,
        )
    )

    version = int(
        value.get(
            "version",
            1,
        )
    )

    status = str(
        value.get(
            "status",
            "active",
        )
    ).strip()

    supersedes = (
        value.get(
            "supersedes",
            [],
        )
        or []
    )

    if isinstance(
        supersedes,
        str,
    ):
        supersedes = [
            supersedes
        ]

    supersedes = sorted(
        {
            str(
                item
            ).strip()
            for item in supersedes
            if str(
                item
            ).strip()
        }
    )

    provenance = dict(
        default_provenance
    )

    provided_provenance = (
        value.get(
            "provenance",
            {},
        )
        or {}
    )

    if not isinstance(
        provided_provenance,
        dict,
    ):
        raise living_governance_error(
            "provenance must be an object"
        )

    provenance.update(
        provided_provenance
    )

    return {
        "schema":
            schema,

        "id":
            semantic_id,

        "stream":
            stream,

        "version":
            version,

        "status":
            status,

        "authority":
            authority,

        "authority_rank":
            authority_order[
                authority
            ],

        "priority":
            priority,

        "text":
            text,

        "supersedes":
            supersedes,

        "dependencies":
            normalize_dependencies(
                value.get(
                    "dependencies",
                    [],
                )
            ),

        "relationships":
            normalize_relationships(
                value.get(
                    "relationships",
                    [],
                )
            ),

        "provenance":
            provenance,
    }


def bootstrap_records() -> list[
    dict[str, Any]
]:
    document = read_json(
        bootstrap_path
    )

    streams = document.get(
        "streams"
    )

    if not isinstance(
        streams,
        dict,
    ):
        raise living_governance_error(
            (
                "bootstrap streams "
                "must be an object"
            )
        )

    authority = str(
        document.get(
            "authority",
            "current_user_directive",
        )
    )

    created_at = str(
        document.get(
            "created_at",
            "",
        )
        or utc_now()
    )

    provenance = {
        "asserted_by":
            "user",

        "method":
            "living-governance-bootstrap",

        "sources": [
            (
                "current user directive "
                "2026-08-30"
            ),
            (
                "project source files "
                "and accepted savant context"
            ),
        ],

        "created_at":
            created_at,
    }

    records:
        list[
            dict[
                str,
                Any,
            ]
        ] = []

    for stream in sorted(
        streams
    ):
        values = streams[
            stream
        ]

        if not isinstance(
            values,
            list,
        ):
            raise living_governance_error(
                (
                    "stream must contain "
                    "a list: "
                    + stream
                )
            )

        for value in values:
            if not isinstance(
                value,
                dict,
            ):
                raise living_governance_error(
                    (
                        "stream record "
                        "must be an object: "
                        + stream
                    )
                )

            records.append(
                normalize_record(
                    value,
                    stream=stream,
                    default_authority=authority,
                    default_provenance=provenance,
                )
            )

    return records


def read_events() -> list[
    dict[str, Any]
]:
    if not ledger_path.exists():
        return []

    events:
        list[
            dict[
                str,
                Any,
            ]
        ] = []

    previous_hash = (
        "0" * 64
    )

    with ledger_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, line in enumerate(
            handle,
            start=1,
        ):
            stripped = line.strip()

            if not stripped:
                continue

            try:
                event = json.loads(
                    stripped
                )
            except json.JSONDecodeError as exc:
                raise living_governance_error(
                    (
                        "ledger json failure "
                        f"at line {line_number}: "
                        f"{exc}"
                    )
                ) from exc

            if event.get(
                "seq"
            ) != len(
                events
            ) + 1:
                raise living_governance_error(
                    (
                        "ledger sequence failure "
                        f"at line {line_number}"
                    )
                )

            if event.get(
                "prev_hash"
            ) != previous_hash:
                raise living_governance_error(
                    (
                        "ledger chain failure "
                        f"at line {line_number}"
                    )
                )

            supplied_hash = str(
                event.get(
                    "hash",
                    "",
                )
            )

            payload = dict(
                event
            )

            payload.pop(
                "hash",
                None,
            )

            calculated_hash = sha256_text(
                canonical_json(
                    payload
                )
            )

            if (
                supplied_hash
                != calculated_hash
            ):
                raise living_governance_error(
                    (
                        "ledger hash failure "
                        f"at line {line_number}"
                    )
                )

            previous_hash = (
                supplied_hash
            )

            events.append(
                event
            )

    return events


def append_event(
    record: dict[str, Any],
    *,
    asserted_at: str | None = None,
) -> dict[str, Any]:
    events = read_events()

    sequence = (
        len(
            events
        )
        + 1
    )

    previous_hash = (
        events[
            -1
        ][
            "hash"
        ]
        if events
        else (
            "0"
            * 64
        )
    )

    event = {
        "seq":
            sequence,

        "event":
            "assert",

        "asserted_at":
            (
                asserted_at
                or utc_now()
            ),

        "prev_hash":
            previous_hash,

        "record":
            record,
    }

    event[
        "hash"
    ] = sha256_text(
        canonical_json(
            event
        )
    )

    authority_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    with ledger_path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            canonical_json(
                event
            )
        )

        handle.write(
            "\n"
        )

        handle.flush()

        os.fsync(
            handle.fileno()
        )

    return event


def init() -> None:
    authority_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    projection_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing = read_events()

    if not existing:
        document = read_json(
            bootstrap_path
        )

        asserted_at = str(
            document.get(
                "created_at",
                "",
            )
            or utc_now()
        )

        for record in bootstrap_records():
            append_event(
                record,
                asserted_at=asserted_at,
            )

    project()


def resolved_records(
    events: Iterable[
        dict[str, Any]
    ] | None = None,
) -> tuple[
    dict[str, Any],
    ...
]:
    source = (
        list(
            events
        )
        if events
        is not None
        else read_events()
    )

    grouped:
        dict[
            tuple[
                str,
                str,
            ],
            list[
                dict[
                    str,
                    Any,
                ]
            ],
        ] = defaultdict(
            list
        )

    for event in source:
        record = event.get(
            "record",
            {}
        )

        if not isinstance(
            record,
            dict,
        ):
            continue

        stream = str(
            record.get(
                "stream",
                "",
            )
        )

        semantic_id = str(
            record.get(
                "id",
                "",
            )
        )

        if (
            not stream
            or not semantic_id
        ):
            continue

        combined = dict(
            record
        )

        combined[
            "_seq"
        ] = int(
            event.get(
                "seq",
                0,
            )
        )

        combined[
            "_event_hash"
        ] = str(
            event.get(
                "hash",
                "",
            )
        )

        combined[
            "_asserted_at"
        ] = str(
            event.get(
                "asserted_at",
                "",
            )
        )

        grouped[
            (
                stream,
                semantic_id,
            )
        ].append(
            combined
        )

    resolved:
        list[
            dict[
                str,
                Any,
            ]
        ] = []

    for values in grouped.values():
        values.sort(
            key=lambda item: (
                int(
                    item.get(
                        "authority_rank",
                        1000,
                    )
                ),
                -int(
                    item.get(
                        "version",
                        0,
                    )
                ),
                -int(
                    item.get(
                        "_seq",
                        0,
                    )
                ),
            )
        )

        selected = values[
            0
        ]

        if selected.get(
            "status"
        ) in {
            "superseded",
            "withdrawn",
            "inactive",
        }:
            continue

        resolved.append(
            selected
        )

    return tuple(
        sorted(
            resolved,
            key=lambda item: (
                str(
                    item.get(
                        "stream",
                        "",
                    )
                ),
                int(
                    item.get(
                        "priority",
                        1000,
                    )
                ),
                str(
                    item.get(
                        "id",
                        "",
                    )
                ),
            ),
        )
    )


def stream_records(
    stream: str,
) -> tuple[
    dict[str, Any],
    ...
]:
    return tuple(
        record
        for record
        in resolved_records()
        if record.get(
            "stream"
        ) == stream
    )


def all_streams() -> tuple[
    str,
    ...
]:
    return tuple(
        sorted(
            {
                str(
                    record.get(
                        "stream",
                        "",
                    )
                )
                for record
                in resolved_records()
                if record.get(
                    "stream"
                )
            }
        )
    )


def dependency_graph(
    records: Iterable[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    values = list(
        records
    )

    nodes = [
        {
            "id":
                record[
                    "id"
                ],

            "stream":
                record[
                    "stream"
                ],

            "authority":
                record[
                    "authority"
                ],

            "version":
                record[
                    "version"
                ],
        }
        for record
        in values
    ]

    edges:
        list[
            dict[
                str,
                str,
            ]
        ] = []

    reverse:
        dict[
            str,
            list[str],
        ] = defaultdict(
            list
        )

    for record in values:
        source = str(
            record[
                "id"
            ]
        )

        for target in record.get(
            "dependencies",
            [],
        ):
            edges.append(
                {
                    "kind":
                        "depends_on",

                    "source":
                        source,

                    "target":
                        target,
                }
            )

            reverse[
                target
            ].append(
                source
            )

        for relationship in record.get(
            "relationships",
            [],
        ):
            edges.append(
                {
                    "kind":
                        str(
                            relationship[
                                "kind"
                            ]
                        ),

                    "source":
                        source,

                    "target":
                        str(
                            relationship[
                                "target"
                            ]
                        ),
                }
            )

    return {
        "schema":
            (
                "savant.living-governance."
                "graph.v1"
            ),

        "nodes":
            sorted(
                nodes,
                key=lambda item:
                    item[
                        "id"
                    ],
            ),

        "edges":
            sorted(
                edges,
                key=lambda item: (
                    item[
                        "source"
                    ],
                    item[
                        "kind"
                    ],
                    item[
                        "target"
                    ],
                ),
            ),

        "reverse_dependencies": {
            key:
                sorted(
                    set(
                        values
                    )
                )
            for key, values
            in sorted(
                reverse.items()
            )
        },
    }


def detect_conflicts(
    events: Iterable[
        dict[str, Any]
    ] | None = None,
) -> list[
    dict[str, Any]
]:
    source = (
        list(
            events
        )
        if events
        is not None
        else read_events()
    )

    grouped:
        dict[
            tuple[
                str,
                str,
            ],
            list[
                dict[
                    str,
                    Any,
                ]
            ],
        ] = defaultdict(
            list
        )

    for event in source:
        record = event.get(
            "record"
        )

        if not isinstance(
            record,
            dict,
        ):
            continue

        grouped[
            (
                str(
                    record.get(
                        "stream",
                        "",
                    )
                ),
                str(
                    record.get(
                        "id",
                        "",
                    )
                ),
            )
        ].append(
            record
        )

    conflicts:
        list[
            dict[
                str,
                Any,
            ]
        ] = []

    for (
        stream,
        semantic_id,
    ), values in grouped.items():
        active = [
            value
            for value
            in values
            if value.get(
                "status"
            )
            not in {
                "superseded",
                "withdrawn",
                "inactive",
            }
        ]

        if len(
            active
        ) < 2:
            continue

        best_rank = min(
            int(
                value.get(
                    "authority_rank",
                    1000,
                )
            )
            for value
            in active
        )

        strongest = [
            value
            for value
            in active
            if int(
                value.get(
                    "authority_rank",
                    1000,
                )
            )
            == best_rank
        ]

        texts = {
            str(
                value.get(
                    "text",
                    "",
                )
            )
            for value
            in strongest
        }

        if len(
            texts
        ) > 1:
            conflicts.append(
                {
                    "stream":
                        stream,

                    "id":
                        semantic_id,

                    "authority_rank":
                        best_rank,

                    "versions":
                        sorted(
                            int(
                                value.get(
                                    "version",
                                    0,
                                )
                            )
                            for value
                            in strongest
                        ),

                    "resolution":
                        "authority_required",
                }
            )

    return sorted(
        conflicts,
        key=lambda item: (
            item[
                "stream"
            ],
            item[
                "id"
            ],
        ),
    )


def projection_digest(
    records: Iterable[
        dict[str, Any]
    ],
) -> str:
    canonical = []

    for record in records:
        value = dict(
            record
        )

        for key in tuple(
            value
        ):
            if key.startswith(
                "_"
            ):
                value.pop(
                    key,
                    None,
                )

        canonical.append(
            value
        )

    return sha256_text(
        canonical_json(
            canonical
        )
    )


def markdown_projection(
    stream: str,
    records: Iterable[
        dict[str, Any]
    ],
    digest: str,
) -> str:
    values = list(
        records
    )

    title = stream.replace(
        "_",
        " ",
    )

    lines = [
        f"# {title}",
        "",
        (
            "> generated living projection. "
            "do not edit as authority."
        ),
        "",
        f"- stream: `{stream}`",
        f"- records: `{len(values)}`",
        f"- authority digest: `{digest}`",
        "",
    ]

    for record in values:
        lines.extend(
            [
                (
                    "## "
                    + str(
                        record[
                            "id"
                        ]
                    )
                ),
                "",
                (
                    "- authority: `"
                    + str(
                        record[
                            "authority"
                        ]
                    )
                    + "`"
                ),
                (
                    "- version: `"
                    + str(
                        record[
                            "version"
                        ]
                    )
                    + "`"
                ),
                (
                    "- status: `"
                    + str(
                        record[
                            "status"
                        ]
                    )
                    + "`"
                ),
                (
                    "- priority: `"
                    + str(
                        record[
                            "priority"
                        ]
                    )
                    + "`"
                ),
                "",
                str(
                    record[
                        "text"
                    ]
                ),
                "",
            ]
        )

        dependencies = record.get(
            "dependencies",
            [],
        )

        if dependencies:
            lines.extend(
                [
                    "### dependencies",
                    "",
                ]
            )

            for dependency in dependencies:
                lines.append(
                    (
                        "- `"
                        + dependency
                        + "`"
                    )
                )

            lines.append(
                ""
            )

        relationships = record.get(
            "relationships",
            [],
        )

        if relationships:
            lines.extend(
                [
                    "### relationships",
                    "",
                ]
            )

            for relationship in relationships:
                lines.append(
                    (
                        "- `"
                        + relationship[
                            "kind"
                        ]
                        + "` → `"
                        + relationship[
                            "target"
                        ]
                        + "`"
                    )
                )

            lines.append(
                ""
            )

        supersedes = record.get(
            "supersedes",
            [],
        )

        if supersedes:
            lines.extend(
                [
                    "### supersedes",
                    "",
                ]
            )

            for target in supersedes:
                lines.append(
                    (
                        "- `"
                        + target
                        + "`"
                    )
                )

            lines.append(
                ""
            )

        provenance = record.get(
            "provenance",
            {},
        )

        if provenance:
            lines.extend(
                [
                    "### provenance",
                    "",
                    "```json",
                    json.dumps(
                        provenance,
                        indent=2,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "```",
                    "",
                ]
            )

    return (
        "\n".join(
            lines
        ).rstrip()
        + "\n"
    )


def project() -> dict[str, Any]:
    events = read_events()

    records = resolved_records(
        events
    )

    digest = projection_digest(
        records
    )

    projection_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    streams:
        dict[
            str,
            list[
                dict[
                    str,
                    Any,
                ]
            ],
        ] = defaultdict(
            list
        )

    clean_records:
        list[
            dict[
                str,
                Any,
            ]
        ] = []

    for record in records:
        clean = {
            key:
                value
            for key, value
            in record.items()
            if not key.startswith(
                "_"
            )
        }

        streams[
            str(
                clean[
                    "stream"
                ]
            )
        ].append(
            clean
        )

        clean_records.append(
            clean
        )

    for stream in sorted(
        streams
    ):
        values = sorted(
            streams[
                stream
            ],
            key=lambda item: (
                int(
                    item.get(
                        "priority",
                        1000,
                    )
                ),
                str(
                    item.get(
                        "id",
                        "",
                    )
                ),
            ),
        )

        stream_digest = (
            projection_digest(
                values
            )
        )

        atomic_write(
            (
                projection_root
                / (
                    stream
                    + ".md"
                )
            ),
            markdown_projection(
                stream,
                values,
                stream_digest,
            ),
        )

        atomic_write(
            (
                projection_root
                / (
                    stream
                    + ".json"
                )
            ),
            (
                json.dumps(
                    {
                        "schema":
                            (
                                "savant.living-"
                                "projection.v1"
                            ),

                        "stream":
                            stream,

                        "digest":
                            stream_digest,

                        "records":
                            values,
                    },
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            ),
        )

    graph = dependency_graph(
        clean_records
    )

    conflicts = detect_conflicts(
        events
    )

    snapshot = {
        "schema":
            (
                "savant.living-governance."
                "snapshot.v1"
            ),

        "digest":
            digest,

        "event_count":
            len(
                events
            ),

        "record_count":
            len(
                clean_records
            ),

        "streams": {
            stream:
                len(
                    values
                )
            for stream, values
            in sorted(
                streams.items()
            )
        },

        "conflicts":
            conflicts,

        "records":
            clean_records,
    }

    atomic_write(
        snapshot_path,
        (
            json.dumps(
                snapshot,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        ),
    )

    atomic_write(
        graph_path,
        (
            json.dumps(
                graph,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        ),
    )

    status = {
        "schema":
            (
                "savant.living-governance."
                "status.v1"
            ),

        "owner":
            "savant",

        "authority_effect":
            "governance",

        "ledger_present":
            ledger_path.exists(),

        "ledger_events":
            len(
                events
            ),

        "current_records":
            len(
                clean_records
            ),

        "streams":
            sorted(
                streams
            ),

        "conflict_count":
            len(
                conflicts
            ),

        "digest":
            digest,

        "projection_root":
            str(
                projection_root
            ),

        "credential_values_exposed":
            False,
    }

    atomic_write(
        status_path,
        (
            json.dumps(
                status,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        ),
    )

    return status


def next_version(
    stream: str,
    semantic_id: str,
) -> int:
    versions = []

    for event in read_events():
        record = event.get(
            "record"
        )

        if not isinstance(
            record,
            dict,
        ):
            continue

        if (
            record.get(
                "stream"
            )
            == stream
            and record.get(
                "id"
            )
            == semantic_id
        ):
            versions.append(
                int(
                    record.get(
                        "version",
                        0,
                    )
                )
            )

    return (
        max(
            versions,
            default=0,
        )
        + 1
    )


def assert_record(
    *,
    stream: str,
    semantic_id: str,
    text: str,
    authority: str,
    priority: int,
    status: str,
    supersedes: list[str],
    dependencies: list[str],
    relationships: list[
        dict[
            str,
            str,
        ]
    ],
    asserted_by: str,
    source: list[str],
) -> dict[str, Any]:
    if (
        authority
        not in authority_order
    ):
        raise living_governance_error(
            (
                "unknown authority class: "
                + authority
            )
        )

    provenance = {
        "asserted_by":
            asserted_by,

        "method":
            "living-governance-contribution",

        "sources":
            sorted(
                set(
                    source
                )
            ),

        "created_at":
            utc_now(),
    }

    record = normalize_record(
        {
            "id":
                semantic_id,

            "version":
                next_version(
                    stream,
                    semantic_id,
                ),

            "priority":
                priority,

            "text":
                text,

            "status":
                status,

            "authority":
                authority,

            "supersedes":
                supersedes,

            "dependencies":
                dependencies,

            "relationships":
                relationships,

            "provenance":
                provenance,
        },
        stream=stream,
        default_authority=authority,
        default_provenance=provenance,
    )

    event = append_event(
        record
    )

    project()

    return event


def history(
    stream: str | None = None,
    semantic_id: str | None = None,
) -> list[
    dict[str, Any]
]:
    output = []

    for event in read_events():
        record = event.get(
            "record"
        )

        if not isinstance(
            record,
            dict,
        ):
            continue

        if (
            stream is not None
            and record.get(
                "stream"
            )
            != stream
        ):
            continue

        if (
            semantic_id is not None
            and record.get(
                "id"
            )
            != semantic_id
        ):
            continue

        output.append(
            event
        )

    return output


def validate() -> dict[str, Any]:
    events = read_events()

    records = resolved_records(
        events
    )

    conflicts = detect_conflicts(
        events
    )

    ids = {
        str(
            record[
                "id"
            ]
        )
        for record in records
    }

    unresolved_dependencies = []

    for record in records:
        for dependency in record.get(
            "dependencies",
            [],
        ):
            if (
                dependency
                not in ids
            ):
                unresolved_dependencies.append(
                    {
                        "id":
                            record[
                                "id"
                            ],

                        "dependency":
                            dependency,
                    }
                )

    report = {
        "valid":
            not conflicts,

        "ledger_events":
            len(
                events
            ),

        "current_records":
            len(
                records
            ),

        "conflicts":
            conflicts,

        "unresolved_dependencies":
            sorted(
                unresolved_dependencies,
                key=lambda item: (
                    item[
                        "id"
                    ],
                    item[
                        "dependency"
                    ],
                ),
            ),

        "digest":
            projection_digest(
                records
            ),
    }

    return report


def parse_relationship(
    value: str,
) -> dict[str, str]:
    kind, separator, target = (
        value.partition(
            ":"
        )
    )

    if (
        not separator
        or not kind.strip()
        or not target.strip()
    ):
        raise argparse.ArgumentTypeError(
            (
                "relationship must be "
                "kind:target"
            )
        )

    return {
        "kind":
            kind.strip(),

        "target":
            target.strip(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="living-governance",
        description=(
            "append-only living governance "
            "and deterministic projections"
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "init"
    )

    subparsers.add_parser(
        "project"
    )

    subparsers.add_parser(
        "status"
    )

    subparsers.add_parser(
        "validate"
    )

    streams_parser = (
        subparsers.add_parser(
            "streams"
        )
    )

    show_parser = (
        subparsers.add_parser(
            "show"
        )
    )

    show_parser.add_argument(
        "stream"
    )

    history_parser = (
        subparsers.add_parser(
            "history"
        )
    )

    history_parser.add_argument(
        "--stream"
    )

    history_parser.add_argument(
        "--id"
    )

    assert_parser = (
        subparsers.add_parser(
            "assert"
        )
    )

    assert_parser.add_argument(
        "--stream",
        required=True,
    )

    assert_parser.add_argument(
        "--id",
        required=True,
    )

    assert_parser.add_argument(
        "--text",
        required=True,
    )

    assert_parser.add_argument(
        "--authority",
        choices=tuple(
            authority_order
        ),
        default=(
            "current_user_directive"
        ),
    )

    assert_parser.add_argument(
        "--priority",
        type=int,
        default=1000,
    )

    assert_parser.add_argument(
        "--status",
        default="active",
    )

    assert_parser.add_argument(
        "--supersedes",
        action="append",
        default=[],
    )

    assert_parser.add_argument(
        "--dependency",
        action="append",
        default=[],
    )

    assert_parser.add_argument(
        "--relationship",
        action="append",
        type=parse_relationship,
        default=[],
    )

    assert_parser.add_argument(
        "--asserted-by",
        default="user",
    )

    assert_parser.add_argument(
        "--source",
        action="append",
        default=[],
    )

    return parser


def main() -> int:
    parser = build_parser()

    args = parser.parse_args()

    try:
        if args.command == "init":
            init()

            output = project()

        elif args.command == "project":
            output = project()

        elif args.command == "status":
            if not ledger_path.exists():
                raise living_governance_error(
                    (
                        "living governance is "
                        "not initialized"
                    )
                )

            output = project()

        elif args.command == "validate":
            output = validate()

        elif args.command == "streams":
            output = {
                "streams":
                    all_streams()
            }

        elif args.command == "show":
            output = {
                "stream":
                    args.stream,

                "records":
                    stream_records(
                        args.stream
                    ),
            }

        elif args.command == "history":
            output = {
                "events":
                    history(
                        stream=args.stream,
                        semantic_id=args.id,
                    )
            }

        elif args.command == "assert":
            output = assert_record(
                stream=args.stream,
                semantic_id=args.id,
                text=args.text,
                authority=args.authority,
                priority=args.priority,
                status=args.status,
                supersedes=args.supersedes,
                dependencies=args.dependency,
                relationships=args.relationship,
                asserted_by=args.asserted_by,
                source=args.source,
            )

        else:
            parser.error(
                "unknown command"
            )

            return 2

    except living_governance_error as exc:
        print(
            json.dumps(
                {
                    "ok":
                        False,

                    "error":
                        str(
                            exc
                        ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            default=list,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
