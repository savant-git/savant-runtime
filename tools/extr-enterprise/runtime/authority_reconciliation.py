#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any, Iterable, Mapping


schema = (
    "savant://runtime/sieve/"
    "authority-reconciliation/1.0.0"
)

selftest_schema = (
    "savant://runtime/sieve/"
    "authority-reconciliation-selftest/1.0.0"
)

owner = "sieve"
authority_effect = "none"

accepted_decision_rank = 3
constitutional_canon_rank = 4

maximum_matches = 8

minimum_overlap_tokens = 3
minimum_candidate_coverage = 0.45

message_schema = (
    "savant://runtime/sieve/"
    "chatgpt-message/1.0.0"
)

evolution_schema = (
    "savant://runtime/sieve/"
    "authority-evolution-candidate/1.0.0"
)

ad_id_pattern = re.compile(
    r"\bAD-\d{8}-\d{3}\b",
    re.IGNORECASE,
)

word_pattern = re.compile(
    r"[a-zA-Z][a-zA-Z0-9_-]*"
)

heading_pattern = re.compile(
    r"(?m)^##\s+([^\n]+?)\s*$"
)

stopwords = frozenset(
    {
        "about",
        "after",
        "again",
        "against",
        "also",
        "among",
        "another",
        "because",
        "before",
        "being",
        "between",
        "both",
        "could",
        "does",
        "each",
        "from",
        "have",
        "into",
        "more",
        "must",
        "only",
        "other",
        "should",
        "some",
        "such",
        "than",
        "that",
        "their",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "under",
        "using",
        "very",
        "what",
        "when",
        "where",
        "which",
        "while",
        "with",
        "would",
        "savant",
        "accepted",
        "decision",
        "authority",
        "current",
        "canonical",
        "status",
    }
)


class reconciliation_error(
    RuntimeError
):
    pass


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
        default=str,
    )


def sha256_bytes(
    data: bytes,
) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def stable_id(
    prefix: str,
    value: Any,
) -> str:
    return (
        prefix
        + ":"
        + sha256_bytes(
            canonical_json(
                value
            ).encode(
                "utf-8"
            )
        )
    )


def read_regular(
    path: Path,
) -> bytes:
    info = path.lstat()

    if (
        stat.S_ISLNK(
            info.st_mode
        )
        or not stat.S_ISREG(
            info.st_mode
        )
    ):
        raise reconciliation_error(
            "refusing non-regular file: "
            f"{path}"
        )

    return path.read_bytes()


def normalize(
    value: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.strip().casefold(),
    )


def tokens(
    value: str,
) -> tuple[
    str,
    ...,
]:
    found: set[
        str
    ] = set()

    for raw in word_pattern.findall(
        value
    ):
        token = raw.casefold()

        if (
            len(
                token
            )
            < 3
            or token
            in stopwords
        ):
            continue

        found.add(
            token
        )

    return tuple(
        sorted(
            found
        )
    )


def markdown_sections(
    text: str,
) -> dict[
    str,
    str,
]:
    matches = list(
        heading_pattern.finditer(
            text
        )
    )

    sections: dict[
        str,
        str,
    ] = {}

    for (
        index,
        match,
    ) in enumerate(
        matches
    ):
        start = match.end()

        end = (
            matches[
                index + 1
            ].start()
            if (
                index + 1
                < len(
                    matches
                )
            )
            else len(
                text
            )
        )

        key = normalize(
            match.group(
                1
            )
        )

        sections[
            key
        ] = (
            text[
                start:end
            ].strip()
        )

    return sections


def decision_identity(
    path: Path,
    text: str,
) -> str:
    match = (
        ad_id_pattern.search(
            path.stem
        )
    )

    if match is None:
        match = (
            ad_id_pattern.search(
                text[
                    :512
                ]
            )
        )

    if match is None:
        raise reconciliation_error(
            "accepted decision lacks "
            f"AD identity: {path}"
        )

    return (
        match.group(
            0
        ).upper()
    )


def accepted_decisions(
    directory: Path,
) -> list[
    dict[
        str,
        Any,
    ]
]:
    if not directory.is_dir():
        raise reconciliation_error(
            "accepted-decisions directory "
            f"unavailable: {directory}"
        )

    records: list[
        dict[
            str,
            Any,
        ]
    ] = []

    seen: set[
        str
    ] = set()

    for path in sorted(
        directory.iterdir(),
        key=lambda item:
            item.name.casefold(),
    ):
        if (
            path.suffix.casefold()
            != ".md"
        ):
            continue

        raw = read_regular(
            path
        )

        text = raw.decode(
            "utf-8"
        )

        sections = (
            markdown_sections(
                text
            )
        )

        status = normalize(
            sections.get(
                "status",
                "",
            )
        )

        if status != "accepted":
            continue

        identity = (
            decision_identity(
                path,
                text,
            )
        )

        if identity in seen:
            raise reconciliation_error(
                "duplicate accepted decision "
                f"identity: {identity}"
            )

        seen.add(
            identity
        )

        supersedes_text = (
            sections.get(
                "supersedes",
                "",
            )
        )

        supersedes = sorted(
            {
                item.upper()
                for item
                in (
                    ad_id_pattern.findall(
                        supersedes_text
                    )
                )
                if (
                    item.upper()
                    != identity
                )
            }
        )

        records.append(
            {
                "authority_kind":
                    "accepted-decision",

                "authority_rank":
                    accepted_decision_rank,

                "id":
                    identity,

                "path":
                    str(
                        path
                    ),

                "sha256":
                    sha256_bytes(
                        raw
                    ),

                "status":
                    "accepted",

                "date":
                    (
                        sections.get(
                            "date"
                        )
                        or None
                    ),

                "supersedes":
                    supersedes,

                "superseded_by":
                    [],

                "search_text":
                    text,

                "search_tokens":
                    tokens(
                        text
                    ),

                "canonical_names":
                    [],
            }
        )

    by_id = {
        record[
            "id"
        ]:
            record
        for record
        in records
    }

    for record in records:
        for prior in record[
            "supersedes"
        ]:
            if prior in by_id:
                (
                    by_id[
                        prior
                    ][
                        "superseded_by"
                    ]
                    .append(
                        record[
                            "id"
                        ]
                    )
                )

    for record in records:
        record[
            "superseded_by"
        ] = sorted(
            set(
                record[
                    "superseded_by"
                ]
            )
        )

    return records


def scalar_text(
    value: Any,
) -> Iterable[
    str
]:
    if (
        value is None
        or isinstance(
            value,
            bool,
        )
    ):
        return

    if isinstance(
        value,
        (
            str,
            int,
            float,
        ),
    ):
        yield str(
            value
        )

        return

    if isinstance(
        value,
        Mapping,
    ):
        for key in sorted(
            value,
            key=lambda item:
                str(
                    item
                ),
        ):
            yield from (
                scalar_text(
                    value[
                        key
                    ]
                )
            )

        return

    if isinstance(
        value,
        list,
    ):
        for item in value:
            yield from (
                scalar_text(
                    item
                )
            )


def constitutional_records(
    path: Path,
) -> tuple[
    list[
        dict[
            str,
            Any,
        ]
    ],
    str,
]:
    raw = read_regular(
        path
    )

    try:
        root = json.loads(
            raw.decode(
                "utf-8"
            )
        )

    except Exception as exc:
        raise reconciliation_error(
            "invalid constitutional "
            f"catalog JSON: {path}"
        ) from exc

    if (
        not isinstance(
            root,
            Mapping,
        )
        or not isinstance(
            root.get(
                "objects"
            ),
            list,
        )
    ):
        raise reconciliation_error(
            "constitutional catalog "
            "must contain an objects list"
        )

    records: list[
        dict[
            str,
            Any,
        ]
    ] = []

    seen: set[
        str
    ] = set()

    for obj in root[
        "objects"
    ]:
        if not isinstance(
            obj,
            Mapping,
        ):
            continue

        authority = (
            obj.get(
                "authority"
            )
        )

        if (
            not isinstance(
                authority,
                Mapping,
            )
            or normalize(
                str(
                    authority.get(
                        "state",
                        "",
                    )
                )
            )
            != "accepted"
        ):
            continue

        identity = obj.get(
            "id"
        )

        if (
            not isinstance(
                identity,
                str,
            )
            or not identity
        ):
            raise reconciliation_error(
                "accepted constitutional "
                "object lacks id"
            )

        if identity in seen:
            raise reconciliation_error(
                "duplicate constitutional "
                f"object identity: {identity}"
            )

        seen.add(
            identity
        )

        lineage = (
            obj.get(
                "lineage"
            )
            if isinstance(
                obj.get(
                    "lineage"
                ),
                Mapping,
            )
            else {}
        )

        supersedes = sorted(
            str(
                item
            )
            for item
            in lineage.get(
                "supersedes",
                [],
            )
            if isinstance(
                item,
                str,
            )
        )

        superseded_by = sorted(
            str(
                item
            )
            for item
            in lineage.get(
                "superseded_by",
                [],
            )
            if isinstance(
                item,
                str,
            )
        )

        canonical_names = [
            str(
                value
            )
            for value
            in (
                obj.get(
                    "canonical_name"
                ),
                obj.get(
                    "display_name"
                ),
            )
            if (
                isinstance(
                    value,
                    str,
                )
                and value.strip()
            )
        ]

        searchable = "\n".join(
            scalar_text(
                obj
            )
        )

        records.append(
            {
                "authority_kind":
                    "constitutional-canon",

                "authority_rank":
                    constitutional_canon_rank,

                "id":
                    identity,

                "path":
                    str(
                        path
                    ),

                "sha256":
                    sha256_bytes(
                        canonical_json(
                            obj
                        ).encode(
                            "utf-8"
                        )
                    ),

                "catalog_sha256":
                    sha256_bytes(
                        raw
                    ),

                "status":
                    obj.get(
                        "status"
                    ),

                "supersedes":
                    supersedes,

                "superseded_by":
                    superseded_by,

                "search_text":
                    searchable,

                "search_tokens":
                    tokens(
                        searchable
                    ),

                "canonical_names":
                    canonical_names,
            }
        )

    records.sort(
        key=lambda record:
            record[
                "id"
            ]
    )

    return (
        records,
        sha256_bytes(
            raw
        ),
    )


def read_jsonl(
    path: Path,
    expected_schema: str,
) -> list[
    dict[
        str,
        Any,
    ]
]:
    raw = read_regular(
        path
    )

    rows: list[
        dict[
            str,
            Any,
        ]
    ] = []

    for (
        line_number,
        line,
    ) in enumerate(
        raw.decode(
            "utf-8"
        ).splitlines(),
        1,
    ):
        if not line.strip():
            continue

        try:
            value = json.loads(
                line
            )

        except Exception as exc:
            raise reconciliation_error(
                "invalid JSONL at "
                f"{path}:{line_number}"
            ) from exc

        if not isinstance(
            value,
            dict,
        ):
            raise reconciliation_error(
                "JSONL row must be object at "
                f"{path}:{line_number}"
            )

        if (
            value.get(
                "schema"
            )
            != expected_schema
        ):
            raise reconciliation_error(
                "unexpected schema at "
                f"{path}:{line_number}: "
                f"{value.get('schema')!r}"
            )

        rows.append(
            value
        )

    return rows


def message_index(
    rows: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
) -> dict[
    str,
    Mapping[
        str,
        Any,
    ],
]:
    result: dict[
        str,
        Mapping[
            str,
            Any,
        ],
    ] = {}

    for row in rows:
        identity = row.get(
            "id"
        )

        text = row.get(
            "text"
        )

        if (
            not isinstance(
                identity,
                str,
            )
            or not identity
        ):
            raise reconciliation_error(
                "message projection lacks id"
            )

        if not isinstance(
            text,
            str,
        ):
            raise reconciliation_error(
                "message projection lacks text: "
                f"{identity}"
            )

        if identity in result:
            raise reconciliation_error(
                "duplicate message projection "
                f"id: {identity}"
            )

        result[
            identity
        ] = row

    return result


def evolution_index(
    rows: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
) -> dict[
    str,
    Mapping[
        str,
        Any,
    ],
]:
    result: dict[
        str,
        Mapping[
            str,
            Any,
        ],
    ] = {}

    for row in rows:
        identity = row.get(
            "source_message_projection_id"
        )

        if (
            not isinstance(
                identity,
                str,
            )
            or not identity
        ):
            raise reconciliation_error(
                "evolution projection lacks "
                "source_message_projection_id"
            )

        if identity in result:
            raise reconciliation_error(
                "duplicate evolution source "
                f"identity: {identity}"
            )

        result[
            identity
        ] = row

    return result


def explicit_decision_ids(
    text: str,
) -> set[
    str
]:
    return {
        item.upper()
        for item
        in (
            ad_id_pattern.findall(
                text
            )
        )
    }


def authority_match(
    text: str,
    candidate_tokens: set[
        str
    ],
    record: Mapping[
        str,
        Any,
    ],
) -> (
    dict[
        str,
        Any,
    ]
    | None
):
    normalized = normalize(
        text
    )

    identity = str(
        record[
            "id"
        ]
    )

    reasons: list[
        str
    ] = []

    score = 0.0

    if (
        record[
            "authority_kind"
        ]
        == "accepted-decision"
        and identity.upper()
        in explicit_decision_ids(
            text
        )
    ):
        reasons.append(
            "explicit-authority-id"
        )

        score = 1.0

    elif (
        identity.casefold()
        in normalized
    ):
        reasons.append(
            "explicit-authority-id"
        )

        score = 1.0

    for name in record.get(
        "canonical_names",
        [],
    ):
        phrase = normalize(
            str(
                name
            )
        )

        if (
            len(
                phrase
            )
            >= 4
            and phrase
            in normalized
        ):
            reasons.append(
                "canonical-name"
            )

            score = max(
                score,
                0.95,
            )

    authority_tokens = set(
        record.get(
            "search_tokens",
            (),
        )
    )

    overlap = sorted(
        candidate_tokens
        & authority_tokens
    )

    coverage = (
        len(
            overlap
        )
        / len(
            candidate_tokens
        )
        if candidate_tokens
        else 0.0
    )

    if (
        len(
            overlap
        )
        >= minimum_overlap_tokens
        and coverage
        >= minimum_candidate_coverage
    ):
        reasons.append(
            "token-overlap"
        )

        score = max(
            score,
            min(
                0.85,
                coverage,
            ),
        )

    if not reasons:
        return None

    return {
        "authority_kind":
            record[
                "authority_kind"
            ],

        "authority_rank":
            record[
                "authority_rank"
            ],

        "authority_id":
            identity,

        "authority_path":
            record[
                "path"
            ],

        "authority_sha256":
            record[
                "sha256"
            ],

        "match_reasons":
            sorted(
                set(
                    reasons
                )
            ),

        "score":
            round(
                score,
                6,
            ),

        "overlap_tokens":
            overlap,

        "candidate_token_coverage":
            round(
                coverage,
                6,
            ),

        "supersedes":
            list(
                record.get(
                    "supersedes",
                    [],
                )
            ),

        "superseded_by":
            list(
                record.get(
                    "superseded_by",
                    [],
                )
            ),
    }


def disposition(
    evolution: Mapping[
        str,
        Any,
    ],
    matches: list[
        dict[
            str,
            Any,
        ]
    ],
) -> str:
    if not matches:
        return "no-match"

    states = set(
        item
        for item
        in evolution.get(
            "candidate_states",
            [],
        )
        if isinstance(
            item,
            str,
        )
    )

    explicit = any(
        "explicit-authority-id"
        in match[
            "match_reasons"
        ]
        for match
        in matches
    )

    superseded_match = any(
        bool(
            match.get(
                "superseded_by"
            )
        )
        for match
        in matches
    )

    if (
        explicit
        and (
            "user-supersession-candidate"
            in states
            or "user-rejection-candidate"
            in states
        )
    ):
        return (
            "higher-authority-"
            "conflict-candidate"
        )

    if (
        explicit
        and "user-acceptance-candidate"
        in states
        and not superseded_match
    ):
        return (
            "corroborated-candidate"
        )

    return (
        "manual-reconciliation-required"
    )


def reconcile(
    messages: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
    evolutions: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
    authorities: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
) -> list[
    dict[
        str,
        Any,
    ]
]:
    messages_by_id = (
        message_index(
            messages
        )
    )

    evolutions_by_id = (
        evolution_index(
            evolutions
        )
    )

    authority_records = list(
        authorities
    )

    output: list[
        dict[
            str,
            Any,
        ]
    ] = []

    for source_id in sorted(
        evolutions_by_id
    ):
        evolution = (
            evolutions_by_id[
                source_id
            ]
        )

        message = (
            messages_by_id.get(
                source_id
            )
        )

        if message is None:
            raise reconciliation_error(
                "evolution source message "
                f"unavailable: {source_id}"
            )

        text = message[
            "text"
        ]

        actual_text_sha256 = (
            sha256_bytes(
                text.encode(
                    "utf-8"
                )
            )
        )

        if (
            evolution.get(
                "source_text_sha256"
            )
            != actual_text_sha256
        ):
            raise reconciliation_error(
                "source text digest mismatch: "
                f"{source_id}"
            )

        if not bool(
            evolution.get(
                "authority_candidate"
            )
        ):
            continue

        candidate_tokens = set(
            tokens(
                text
            )
        )

        matches = [
            match
            for record
            in authority_records
            if (
                match := authority_match(
                    text,
                    candidate_tokens,
                    record,
                )
            )
            is not None
        ]

        matches.sort(
            key=lambda match: (
                match[
                    "authority_rank"
                ],
                -match[
                    "score"
                ],
                match[
                    "authority_kind"
                ],
                match[
                    "authority_id"
                ],
            )
        )

        matches = matches[
            :maximum_matches
        ]

        state = disposition(
            evolution,
            matches,
        )

        output.append(
            {
                "schema":
                    (
                        "savant://runtime/sieve/"
                        "authority-reconciliation-"
                        "record/1.0.0"
                    ),

                "id":
                    stable_id(
                        (
                            "sieve:"
                            "authority-reconciliation"
                        ),
                        {
                            (
                                "source_message_"
                                "projection_id"
                            ):
                                source_id,

                            "source_text_sha256":
                                actual_text_sha256,

                            "authority_matches":
                                [
                                    [
                                        match[
                                            "authority_kind"
                                        ],
                                        match[
                                            "authority_id"
                                        ],
                                        match[
                                            "authority_sha256"
                                        ],
                                    ]
                                    for match
                                    in matches
                                ],

                            "disposition":
                                state,
                        },
                    ),

                "owner":
                    owner,

                "authority_effect":
                    authority_effect,

                "authoritative":
                    False,

                "admission_eligible":
                    False,

                "source_message_projection_id":
                    source_id,

                "source_text_sha256":
                    actual_text_sha256,

                "evolution_projection_id":
                    evolution.get(
                        "id"
                    ),

                "candidate_states":
                    list(
                        evolution.get(
                            "candidate_states",
                            [],
                        )
                    ),

                "authority_candidate":
                    True,

                "disposition":
                    state,

                "reconciliation_required":
                    (
                        state
                        != (
                            "corroborated-"
                            "candidate"
                        )
                    ),

                "authority_matches":
                    matches,

                "lineage":
                    {
                        (
                            "source_message_"
                            "projection_id"
                        ):
                            source_id,

                        "evolution_projection_id":
                            evolution.get(
                                "id"
                            ),

                        "source_text_sha256":
                            actual_text_sha256,
                    },
            }
        )

    output.sort(
        key=lambda row: (
            row[
                "source_message_projection_id"
            ],
            row[
                "id"
            ],
        )
    )

    return output


def jsonl_bytes(
    rows: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
) -> bytes:
    return (
        "".join(
            canonical_json(
                row
            )
            + "\n"
            for row
            in rows
        )
    ).encode(
        "utf-8"
    )


def atomic_write(
    path: Path,
    data: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        descriptor,
        temporary_name,
    ) = tempfile.mkstemp(
        prefix=(
            f".{path.name}."
        ),
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
            "wb",
            closefd=True,
        ) as handle:
            handle.write(
                data
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            path,
        )

        directory = os.open(
            path.parent,
            os.O_RDONLY,
        )

        try:
            os.fsync(
                directory
            )

        finally:
            os.close(
                directory
            )

    finally:
        temporary.unlink(
            missing_ok=True
        )


def build_projection(
    messages_path: Path,
    evolution_path: Path,
    decisions_dir: Path,
    catalog_path: Path,
) -> tuple[
    list[
        dict[
            str,
            Any,
        ]
    ],
    dict[
        str,
        Any,
    ],
]:
    messages = read_jsonl(
        messages_path,
        message_schema,
    )

    evolutions = read_jsonl(
        evolution_path,
        evolution_schema,
    )

    decisions = (
        accepted_decisions(
            decisions_dir
        )
    )

    (
        constitutional,
        catalog_sha256,
    ) = constitutional_records(
        catalog_path
    )

    rows = reconcile(
        messages,
        evolutions,
        [
            *decisions,
            *constitutional,
        ],
    )

    payload = jsonl_bytes(
        rows
    )

    counts: dict[
        str,
        int,
    ] = {}

    for row in rows:
        state = row[
            "disposition"
        ]

        counts[
            state
        ] = (
            counts.get(
                state,
                0,
            )
            + 1
        )

    manifest = {
        "schema":
            schema,

        "owner":
            owner,

        "authority_effect":
            authority_effect,

        "authoritative":
            False,

        "admission_eligible":
            False,

        "rebuildable":
            True,

        "authority_precedence":
            [
                {
                    "rank":
                        accepted_decision_rank,

                    "kind":
                        "accepted-decision",
                },
                {
                    "rank":
                        constitutional_canon_rank,

                    "kind":
                        "constitutional-canon",
                },
            ],

        "sources":
            {
                "messages":
                    {
                        "path":
                            str(
                                messages_path.resolve()
                            ),

                        "sha256":
                            sha256_bytes(
                                read_regular(
                                    messages_path
                                )
                            ),
                    },

                "authority_evolution":
                    {
                        "path":
                            str(
                                evolution_path.resolve()
                            ),

                        "sha256":
                            sha256_bytes(
                                read_regular(
                                    evolution_path
                                )
                            ),
                    },

                "accepted_decisions":
                    {
                        "path":
                            str(
                                decisions_dir.resolve()
                            ),

                        "accepted_records":
                            len(
                                decisions
                            ),

                        "records_digest":
                            sha256_bytes(
                                canonical_json(
                                    [
                                        [
                                            record[
                                                "id"
                                            ],
                                            record[
                                                "sha256"
                                            ],
                                        ]
                                        for record
                                        in decisions
                                    ]
                                ).encode(
                                    "utf-8"
                                )
                            ),
                    },

                "constitutional_catalog":
                    {
                        "path":
                            str(
                                catalog_path.resolve()
                            ),

                        "sha256":
                            catalog_sha256,

                        "accepted_records":
                            len(
                                constitutional
                            ),
                    },
            },

        "counts":
            {
                "records":
                    len(
                        rows
                    ),

                "by_disposition":
                    dict(
                        sorted(
                            counts.items()
                        )
                    ),
            },

        "output":
            {
                "authority_reconciliation.jsonl":
                    {
                        "sha256":
                            sha256_bytes(
                                payload
                            ),

                        "records":
                            len(
                                rows
                            ),
                    }
            },
    }

    return (
        rows,
        manifest,
    )


def write_projection(
    messages_path: Path,
    evolution_path: Path,
    decisions_dir: Path,
    catalog_path: Path,
    output_dir: Path,
) -> dict[
    str,
    Any,
]:
    (
        rows,
        manifest,
    ) = build_projection(
        messages_path,
        evolution_path,
        decisions_dir,
        catalog_path,
    )

    atomic_write(
        (
            output_dir
            / "authority_reconciliation.jsonl"
        ),
        jsonl_bytes(
            rows
        ),
    )

    atomic_write(
        (
            output_dir
            / "manifest.json"
        ),
        (
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode(
            "utf-8"
        ),
    )

    return manifest


def test_message(
    index: int,
    text: str,
) -> dict[
    str,
    Any,
]:
    identity = (
        "message-projection-"
        f"{index}"
    )

    return {
        "schema":
            message_schema,

        "id":
            identity,

        "owner":
            "sieve",

        "authority_effect":
            "none",

        "authoritative":
            False,

        "conversation":
            {
                "id":
                    "conversation-test",
            },

        "graph":
            {
                "node_id":
                    f"node-{index}",

                "is_current_branch":
                    True,
            },

        "message":
            {
                "id":
                    f"message-{index}",

                "author":
                    {
                        "role":
                            "user",
                    },

                "create_time":
                    float(
                        index
                    ),
            },

        "text":
            text,
    }


def test_evolution(
    index: int,
    text: str,
    states: list[
        str
    ],
) -> dict[
    str,
    Any,
]:
    identity = (
        "message-projection-"
        f"{index}"
    )

    return {
        "schema":
            evolution_schema,

        "id":
            f"evolution-{index}",

        "owner":
            "sieve",

        "authority_effect":
            "none",

        "authoritative":
            False,

        "admission_eligible":
            False,

        "source_message_projection_id":
            identity,

        "source_text_sha256":
            sha256_bytes(
                text.encode(
                    "utf-8"
                )
            ),

        "candidate_states":
            states,

        "authority_candidate":
            True,

        "evolution_candidate":
            any(
                (
                    "acceptance"
                    in state
                    or "rejection"
                    in state
                    or "supersession"
                    in state
                )
                for state
                in states
            ),

        "semantic_review_required":
            True,

        "reconciliation_required":
            True,
    }


def selftest() -> dict[
    str,
    Any,
]:
    message_texts = [
        (
            "Accepted. Keep "
            "AD-20260928-001 exactly."
        ),
        (
            "Replace AD-20260928-001 "
            "with four primary edifices."
        ),
        (
            "Use Kinship Service for "
            "functional relationship planes."
        ),
        (
            "Use zebrafish indexing for "
            "this unrelated concept."
        ),
    ]

    states = [
        [
            "user-acceptance-candidate",
        ],
        [
            "user-supersession-candidate",
            "user-directive-candidate",
        ],
        [
            "user-directive-candidate",
        ],
        [
            "user-directive-candidate",
        ],
    ]

    with tempfile.TemporaryDirectory(
        prefix=(
            "sieve-reconciliation-test-"
        )
    ) as temp_name:
        temp = Path(
            temp_name
        )

        decisions = (
            temp
            / "authority"
            / "accepted-decisions"
        )

        decisions.mkdir(
            parents=True
        )

        decision_text = (
            "# AD-20260928-001: "
            "Three Primary Edifices\n"
            "\n"
            "## Status\n"
            "\n"
            "Accepted\n"
            "\n"
            "## Date\n"
            "\n"
            "2026-09-28\n"
            "\n"
            "## Authority\n"
            "\n"
            "Current user directive.\n"
            "\n"
            "## Supersedes\n"
            "\n"
            "None.\n"
            "\n"
            "## Decision\n"
            "\n"
            "Savant has exactly three "
            "primary edifices: identity, "
            "utility, and programming.\n"
        )

        (
            decisions
            / (
                "AD-20260928-001-"
                "three-primary-edifices.md"
            )
        ).write_text(
            decision_text,
            encoding="utf-8",
        )

        catalog = (
            temp
            / "catalog.json"
        )

        catalog.write_text(
            json.dumps(
                {
                    "catalog_id":
                        "test",

                    "objects":
                        [
                            {
                                "id":
                                    "service:kinship",

                                "kind":
                                    "service",

                                "canonical_name":
                                    "Kinship Service",

                                "display_name":
                                    "Kinship Service",

                                "description":
                                    (
                                        "Functional "
                                        "relationship-plane "
                                        "service."
                                    ),

                                "authority":
                                    {
                                        "state":
                                            "accepted",

                                        "tier":
                                            0,

                                        "source":
                                            (
                                                "constitutional-"
                                                "bootstrap"
                                            ),
                                    },

                                "status":
                                    "active",

                                "lineage":
                                    {
                                        "parent":
                                            "domain:services",

                                        "supersedes":
                                            [],

                                        "superseded_by":
                                            [],
                                    },

                                "relationships":
                                    [],

                                "dependencies":
                                    [
                                        "system:kindred"
                                    ],
                            }
                        ],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        messages = [
            test_message(
                index + 1,
                text,
            )
            for (
                index,
                text,
            )
            in enumerate(
                message_texts
            )
        ]

        evolutions = [
            test_evolution(
                index + 1,
                text,
                states[
                    index
                ],
            )
            for (
                index,
                text,
            )
            in enumerate(
                message_texts
            )
        ]

        messages_path = (
            temp
            / "messages.jsonl"
        )

        evolution_path = (
            temp
            / "authority_evolution.jsonl"
        )

        messages_path.write_bytes(
            jsonl_bytes(
                messages
            )
        )

        evolution_path.write_bytes(
            jsonl_bytes(
                evolutions
            )
        )

        (
            first,
            first_manifest,
        ) = build_projection(
            messages_path,
            evolution_path,
            decisions,
            catalog,
        )

        (
            second,
            second_manifest,
        ) = build_projection(
            messages_path,
            evolution_path,
            decisions,
            catalog,
        )

        by_source = {
            row[
                "source_message_projection_id"
            ]:
                row
            for row
            in first
        }

        checks = {
            "authority_none":
                (
                    authority_effect
                    == "none"
                ),

            "four_candidates":
                (
                    len(
                        first
                    )
                    == 4
                ),

            "deterministic_rows":
                (
                    first
                    == second
                ),

            "deterministic_manifest":
                (
                    first_manifest
                    == second_manifest
                ),

            "accepted_decision_precedes_canon":
                (
                    accepted_decision_rank
                    < constitutional_canon_rank
                ),

            "explicit_acceptance_corroborated":
                (
                    by_source[
                        "message-projection-1"
                    ][
                        "disposition"
                    ]
                    == (
                        "corroborated-"
                        "candidate"
                    )
                ),

            "explicit_supersession_conflict":
                (
                    by_source[
                        "message-projection-2"
                    ][
                        "disposition"
                    ]
                    == (
                        "higher-authority-"
                        "conflict-candidate"
                    )
                ),

            "canonical_name_requires_review":
                (
                    by_source[
                        "message-projection-3"
                    ][
                        "disposition"
                    ]
                    == (
                        "manual-"
                        "reconciliation-required"
                    )
                ),

            "unmatched_preserved":
                (
                    by_source[
                        "message-projection-4"
                    ][
                        "disposition"
                    ]
                    == "no-match"
                ),

            "nothing_authoritative":
                all(
                    (
                        row[
                            "authoritative"
                        ]
                        is False
                    )
                    for row
                    in first
                ),

            "nothing_admitted":
                all(
                    (
                        row[
                            "admission_eligible"
                        ]
                        is False
                    )
                    for row
                    in first
                ),

            "text_not_duplicated":
                all(
                    (
                        "text"
                        not in row
                    )
                    for row
                    in first
                ),

            "source_digest_bound":
                all(
                    (
                        row[
                            "source_text_sha256"
                        ]
                        == sha256_bytes(
                            message_texts[
                                index
                            ].encode(
                                "utf-8"
                            )
                        )
                    )
                    for (
                        index,
                        row,
                    )
                    in enumerate(
                        first
                    )
                ),

            "decision_digest_preserved":
                (
                    by_source[
                        "message-projection-1"
                    ][
                        "authority_matches"
                    ][
                        0
                    ][
                        "authority_sha256"
                    ]
                    == sha256_bytes(
                        decision_text.encode(
                            "utf-8"
                        )
                    )
                ),

            "catalog_identity_preserved":
                (
                    by_source[
                        "message-projection-3"
                    ][
                        "authority_matches"
                    ][
                        0
                    ][
                        "authority_id"
                    ]
                    == "service:kinship"
                ),

            "reconciliation_required_on_conflict":
                (
                    by_source[
                        "message-projection-2"
                    ][
                        "reconciliation_required"
                    ]
                    is True
                ),

            "corroboration_not_admission":
                (
                    by_source[
                        "message-projection-1"
                    ][
                        "admission_eligible"
                    ]
                    is False
                ),
        }

        return {
            "schema":
                selftest_schema,

            "ok":
                all(
                    checks.values()
                ),

            "checks":
                checks,

            "count":
                len(
                    first
                ),
        }


def main() -> int:
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "messages",
        nargs="?",
        type=Path,
    )

    parser.add_argument(
        "authority_evolution",
        nargs="?",
        type=Path,
    )

    parser.add_argument(
        "--accepted-decisions",
        type=Path,
        default=Path(
            "/root/savant-runtime/"
            "authority/accepted-decisions"
        ),
    )

    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(
            "/root/savant-runtime/"
            "canon-system/authority/"
            "constitution/catalog.json"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    arguments = (
        parser.parse_args()
    )

    if arguments.selftest:
        result = selftest()

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )

        return (
            0
            if result[
                "ok"
            ]
            else 1
        )

    if arguments.messages is None:
        parser.error(
            "messages.jsonl is required"
        )

    if (
        arguments.authority_evolution
        is None
    ):
        parser.error(
            "authority_evolution.jsonl "
            "is required"
        )

    if arguments.output is None:
        parser.error(
            "--output is required"
        )

    try:
        manifest = (
            write_projection(
                arguments.messages,
                (
                    arguments
                    .authority_evolution
                ),
                (
                    arguments
                    .accepted_decisions
                ),
                arguments.catalog,
                arguments.output,
            )
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema,

                    "ok":
                        False,

                    "error":
                        str(
                            exc
                        ),
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )

        return 1

    print(
        json.dumps(
            {
                "schema":
                    schema,

                "ok":
                    True,

                "output":
                    str(
                        arguments
                        .output
                        .resolve()
                    ),

                "manifest":
                    manifest,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
