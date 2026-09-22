#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


schema_version = (
    "savant.niche.masterplan-projection.v2"
)

authority_effect = "none"

owner = "exile:niche"

savant_root = Path(
    "/root/savant-runtime"
)

masterplan_path = (
    savant_root
    / "authority"
    / "task-graph"
    / "masterplan.json"
)


class MasterplanProjectionError(
    RuntimeError
):
    pass


def canonical_json_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode(
        "utf-8"
    )


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def stable_digest(
    value: Any,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            value
        )
    )


def load_masterplan() -> tuple[
    dict[str, Any],
    str,
]:
    if not masterplan_path.is_file():
        raise MasterplanProjectionError(
            "authoritative masterplan "
            "graph unavailable"
        )

    raw = masterplan_path.read_bytes()

    try:
        value = json.loads(
            raw.decode(
                "utf-8"
            )
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise MasterplanProjectionError(
            "authoritative masterplan "
            "graph is not valid json"
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise MasterplanProjectionError(
            "authoritative masterplan "
            "graph must be an object"
        )

    return (
        value,
        sha256_bytes(
            raw
        ),
    )


def sequence_count(
    value: Any,
) -> int:
    if isinstance(
        value,
        list,
    ):
        return len(
            value
        )

    return 0


def mapping_count(
    value: Any,
) -> int:
    if isinstance(
        value,
        dict,
    ):
        return len(
            value
        )

    return 0


def graph_authority(
    graph: dict[str, Any],
) -> Any:
    value = graph.get(
        "authority"
    )

    if isinstance(
        value,
        dict,
    ):
        return value

    return None


def graph_metrics(
    graph: dict[str, Any],
) -> dict[str, int]:
    return {
        "attestation_count":
            sequence_count(
                graph.get(
                    "attestations"
                )
            ),
        "decision_count":
            sequence_count(
                graph.get(
                    "decisions"
                )
            ),
        "event_count":
            sequence_count(
                graph.get(
                    "events"
                )
            ),
        "record_count":
            sequence_count(
                graph.get(
                    "records"
                )
            ),
        "segue_count":
            sequence_count(
                graph.get(
                    "segues"
                )
            ),
        "top_level_field_count":
            mapping_count(
                graph
            ),
    }


def walk_graph(
    value: Any,
    path: tuple[str, ...] = (),
) -> Iterable[
    tuple[
        tuple[str, ...],
        Any,
    ]
]:
    yield (
        path,
        value,
    )

    if isinstance(
        value,
        dict,
    ):
        for key in sorted(
            value
        ):
            yield from walk_graph(
                value[
                    key
                ],
                path
                + (
                    str(
                        key
                    ),
                ),
            )

    elif isinstance(
        value,
        list,
    ):
        for index, item in enumerate(
            value
        ):
            yield from walk_graph(
                item,
                path
                + (
                    str(
                        index
                    ),
                ),
            )


def pointer(
    path: tuple[str, ...],
) -> str:
    if not path:
        return "/"

    escaped = [
        part.replace(
            "~",
            "~0",
        ).replace(
            "/",
            "~1",
        )
        for part in path
    ]

    return (
        "/"
        + "/".join(
            escaped
        )
    )


def scalar_type(
    value: Any,
) -> str:
    if value is None:
        return "null"

    if isinstance(
        value,
        bool,
    ):
        return "boolean"

    if isinstance(
        value,
        int,
    ):
        return "integer"

    if isinstance(
        value,
        float,
    ):
        return "number"

    if isinstance(
        value,
        str,
    ):
        return "string"

    if isinstance(
        value,
        list,
    ):
        return "array"

    if isinstance(
        value,
        dict,
    ):
        return "object"

    return type(
        value
    ).__name__.lower()


def structural_metrics(
    graph: dict[str, Any],
) -> dict[str, int]:
    counts = {
        "array_count": 0,
        "boolean_count": 0,
        "integer_count": 0,
        "null_count": 0,
        "number_count": 0,
        "object_count": 0,
        "scalar_count": 0,
        "string_count": 0,
        "value_count": 0,
    }

    for _, value in walk_graph(
        graph
    ):
        value_type = scalar_type(
            value
        )

        counts[
            "value_count"
        ] += 1

        if value_type == "object":
            counts[
                "object_count"
            ] += 1

        elif value_type == "array":
            counts[
                "array_count"
            ] += 1

        else:
            counts[
                "scalar_count"
            ] += 1

            key = (
                value_type
                + "_count"
            )

            if key in counts:
                counts[
                    key
                ] += 1

    return counts


def identity_fields() -> tuple[
    str,
    ...,
]:
    return (
        "id",
        "task_id",
        "record_id",
        "event_id",
        "decision_id",
        "segue_id",
        "attestation_id",
    )


def identity_index(
    graph: dict[str, Any],
) -> list[dict[str, Any]]:
    result: list[
        dict[str, Any]
    ] = []

    fields = identity_fields()

    for path, value in walk_graph(
        graph
    ):
        if not isinstance(
            value,
            dict,
        ):
            continue

        for field in fields:
            identity = value.get(
                field
            )

            if not isinstance(
                identity,
                (
                    str,
                    int,
                ),
            ):
                continue

            result.append(
                {
                    "field":
                        field,
                    "identity":
                        str(
                            identity
                        ),
                    "pointer":
                        pointer(
                            path
                        ),
                    "digest":
                        stable_digest(
                            value
                        ),
                }
            )

            break

    result.sort(
        key=lambda item: (
            item[
                "identity"
            ],
            item[
                "field"
            ],
            item[
                "pointer"
            ],
        )
    )

    return result


def duplicate_identities(
    index: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:
    grouped: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for item in index:
        grouped.setdefault(
            item[
                "identity"
            ],
            [],
        ).append(
            item
        )

    duplicates = []

    for identity in sorted(
        grouped
    ):
        members = grouped[
            identity
        ]

        if len(
            members
        ) < 2:
            continue

        duplicates.append(
            {
                "identity":
                    identity,
                "occurrence_count":
                    len(
                        members
                    ),
                "members":
                    members,
            }
        )

    return duplicates


def masterplan_projection() -> dict[
    str,
    Any,
]:
    (
        graph,
        source_sha256,
    ) = load_masterplan()

    graph_digest = stable_digest(
        graph
    )

    identities = identity_index(
        graph
    )

    duplicate_identity_groups = (
        duplicate_identities(
            identities
        )
    )

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "projection":
            True,
        "mutation_authority":
            False,
        "source": {
            "path":
                str(
                    masterplan_path
                ),
            "source_sha256":
                source_sha256,
            "authority":
                graph_authority(
                    graph
                ),
        },
        "graph_digest":
            graph_digest,
        "projection_digest":
            stable_digest(
                {
                    "source_sha256":
                        source_sha256,
                    "graph_digest":
                        graph_digest,
                }
            ),
        "metrics": {
            **graph_metrics(
                graph
            ),
            **structural_metrics(
                graph
            ),
            "identity_count":
                len(
                    identities
                ),
            "duplicate_identity_group_count":
                len(
                    duplicate_identity_groups
                ),
        },
        "identity_index":
            identities,
        "duplicate_identities":
            duplicate_identity_groups,
        "graph":
            graph,
    }


def summary_projection() -> dict[
    str,
    Any,
]:
    projection = (
        masterplan_projection()
    )

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "projection":
            True,
        "mutation_authority":
            False,
        "source":
            projection[
                "source"
            ],
        "graph_digest":
            projection[
                "graph_digest"
            ],
        "projection_digest":
            projection[
                "projection_digest"
            ],
        "metrics":
            projection[
                "metrics"
            ],
        "duplicate_identities":
            projection[
                "duplicate_identities"
            ],
    }


def identity_projection(
    identity: str,
) -> dict[str, Any]:
    projection = (
        masterplan_projection()
    )

    matches = [
        item
        for item
        in projection[
            "identity_index"
        ]
        if item[
            "identity"
        ] == identity
    ]

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "owner":
            owner,
        "projection":
            True,
        "mutation_authority":
            False,
        "identity":
            identity,
        "match_count":
            len(
                matches
            ),
        "matches":
            matches,
        "graph_digest":
            projection[
                "graph_digest"
            ],
    }


def self_check() -> dict[
    str,
    Any,
]:
    first = masterplan_projection()
    second = masterplan_projection()

    if first != second:
        raise MasterplanProjectionError(
            "masterplan projection "
            "is not deterministic"
        )

    if (
        first.get(
            "authority_effect"
        )
        != "none"
    ):
        raise MasterplanProjectionError(
            "projection authority boundary "
            "is invalid"
        )

    if (
        first.get(
            "mutation_authority"
        )
        is not False
    ):
        raise MasterplanProjectionError(
            "projection acquired "
            "mutation authority"
        )

    if (
        first.get(
            "owner"
        )
        != owner
    ):
        raise MasterplanProjectionError(
            "projection owner is invalid"
        )

    if (
        stable_digest(
            first[
                "graph"
            ]
        )
        != first[
            "graph_digest"
        ]
    ):
        raise MasterplanProjectionError(
            "graph digest mismatch"
        )

    identity_keys = [
        (
            item[
                "identity"
            ],
            item[
                "field"
            ],
            item[
                "pointer"
            ],
        )
        for item
        in first[
            "identity_index"
        ]
    ]

    if identity_keys != sorted(
        identity_keys
    ):
        raise MasterplanProjectionError(
            "identity index is not "
            "deterministically ordered"
        )

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "self_check":
            "passed",
        "determinism":
            "passed",
        "mutation_authority":
            False,
        "source_path":
            str(
                masterplan_path
            ),
        "source_sha256":
            first[
                "source"
            ][
                "source_sha256"
            ],
        "graph_digest":
            first[
                "graph_digest"
            ],
        "projection_digest":
            first[
                "projection_digest"
            ],
        "metrics":
            first[
                "metrics"
            ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=(
            "project",
            "summary",
            "identity",
            "self-check",
        ),
    )

    parser.add_argument(
        "value",
        nargs="?",
    )

    arguments = parser.parse_args()

    try:
        if (
            arguments.command
            == "project"
        ):
            result = (
                masterplan_projection()
            )

        elif (
            arguments.command
            == "summary"
        ):
            result = (
                summary_projection()
            )

        elif (
            arguments.command
            == "identity"
        ):
            if arguments.value is None:
                raise (
                    MasterplanProjectionError(
                        "identity value required"
                    )
                )

            result = (
                identity_projection(
                    arguments.value
                )
            )

        else:
            result = self_check()

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema_version,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "failed",
                    "error":
                        str(
                            exc
                        ),
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

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
