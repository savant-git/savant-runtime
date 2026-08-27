#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).expanduser().absolute()

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from runtime.lineage.model import stable_hash  # noqa: E402

from runtime.palaver.graph.runtime_graph_index import (  # noqa: E402
    RuntimeGraphIndex,
)


DEFAULT_GRAPH = (
    ROOT
    / "vault"
    / "graphs"
    / "runtime_graph.json"
)

DEFAULT_FIELDS = (
    ROOT
    / "vault"
    / "fields"
    / "structural_fields.json"
)

DEFAULT_POLICY = (
    ROOT
    / "authority_graph"
    / "policies"
    / "lineage_authority_projection.json"
)

DEFAULT_OUTPUT = (
    ROOT
    / "vault"
    / "authority"
    / "authority_index.json"
)


def read_json(
    path: Path,
    *,
    required: bool = True,
) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise FileNotFoundError(
                f"required JSON file missing: {path}"
            )

        return {}

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(
            f"cannot read JSON file {path}: {exc}"
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise TypeError(
            f"JSON root must be an object: {path}"
        )

    return dict(
        payload
    )


def _integer_mapping(
    value: Any,
    field_name: str,
) -> dict[str, int]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(
            f"{field_name} must be an object"
        )

    result: dict[str, int] = {}

    for key, raw_weight in value.items():
        if (
            isinstance(
                raw_weight,
                bool,
            )
            or not isinstance(
                raw_weight,
                int,
            )
        ):
            raise TypeError(
                f"{field_name}.{key} must be an integer"
            )

        result[
            str(key)
        ] = raw_weight

    return result


def load_policy(
    path: Path = DEFAULT_POLICY,
) -> dict[str, Any]:
    policy = read_json(
        path
    )

    policy[
        "incoming_role_weights"
    ] = _integer_mapping(
        policy.get(
            "incoming_role_weights",
            {},
        ),
        "incoming_role_weights",
    )

    policy[
        "outgoing_role_weights"
    ] = _integer_mapping(
        policy.get(
            "outgoing_role_weights",
            {},
        ),
        "outgoing_role_weights",
    )

    tiers = policy.get(
        "tiers",
        []
    )

    if not isinstance(
        tiers,
        list,
    ) or not tiers:
        raise ValueError(
            "authority policy requires tiers"
        )

    normalized_tiers: list[
        dict[str, Any]
    ] = []

    for tier in tiers:
        if not isinstance(
            tier,
            Mapping,
        ):
            raise TypeError(
                "authority tier must be an object"
            )

        tier_id = str(
            tier.get(
                "id",
                "",
            )
        ).strip()

        minimum = tier.get(
            "minimum_score"
        )

        if (
            not tier_id
            or isinstance(
                minimum,
                bool,
            )
            or not isinstance(
                minimum,
                int,
            )
        ):
            raise ValueError(
                "authority tier requires id "
                "and integer minimum_score"
            )

        normalized_tiers.append({
            "id": tier_id,
            "minimum_score": minimum,
        })

    normalized_tiers.sort(
        key=lambda item: (
            -item[
                "minimum_score"
            ],
            item["id"],
        )
    )

    policy[
        "tiers"
    ] = normalized_tiers

    return policy


def _field_lookup(
    payload: Mapping[
        str,
        Any,
    ] | None,
) -> dict[str, dict[str, Any]]:
    if not isinstance(
        payload,
        Mapping,
    ):
        return {}

    fields = payload.get(
        "fields",
        []
    )

    if not isinstance(
        fields,
        list,
    ):
        return {}

    result: dict[
        str,
        dict[str, Any],
    ] = {}

    for item in fields:
        if not isinstance(
            item,
            Mapping,
        ):
            continue

        node_id = str(
            item.get(
                "id",
                "",
            )
        ).strip()

        if node_id:
            result[
                node_id
            ] = dict(
                item
            )

    return result


def _role_counts(
    edges: list[
        Mapping[str, Any]
    ],
) -> dict[str, int]:
    counts = Counter(
        str(
            edge.get(
                "role",
                "generic",
            )
        )
        for edge in edges
    )

    return dict(
        sorted(
            counts.items()
        )
    )


def _weighted_score(
    counts: Mapping[
        str,
        int,
    ],
    weights: Mapping[
        str,
        int,
    ],
) -> int:
    return sum(
        int(count)
        * int(
            weights.get(
                role,
                0,
            )
        )
        for role, count
        in counts.items()
    )


def _authority_tier(
    score: int,
    *,
    placeholder: bool,
    policy: Mapping[
        str,
        Any,
    ],
) -> str:
    if placeholder:
        return "unresolved"

    for tier in policy[
        "tiers"
    ]:
        if score >= int(
            tier[
                "minimum_score"
            ]
        ):
            return str(
                tier["id"]
            )

    return "derivative"


def compile_authority_index(
    graph_payload: Mapping[
        str,
        Any,
    ],
    *,
    structural_payload: Mapping[
        str,
        Any,
    ] | None = None,
    policy: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    index = RuntimeGraphIndex(
        graph_payload
    )

    field_lookup = _field_lookup(
        structural_payload
    )

    incoming_weights = dict(
        policy[
            "incoming_role_weights"
        ]
    )

    outgoing_weights = dict(
        policy[
            "outgoing_role_weights"
        ]
    )

    governing_roles = {
        str(role)
        for role in policy.get(
            "governing_roles",
            []
        )
    }

    authority_kinds = {
        str(kind).casefold()
        for kind in policy.get(
            "authority_kinds",
            []
        )
    }

    explicit_weight = int(
        policy.get(
            "explicit_authority_weight",
            0,
        )
    )

    kind_weight = int(
        policy.get(
            "authority_kind_weight",
            0,
        )
    )

    placeholder_penalty = int(
        policy.get(
            "placeholder_penalty",
            0,
        )
    )

    records: list[
        dict[str, Any]
    ] = []

    tier_counts: Counter[
        str
    ] = Counter()

    for node in index.node_records():
        node_id = str(
            node["id"]
        )

        incoming = index.incoming_edges(
            node_id,
            active_only=False,
        )

        outgoing = index.outgoing_edges(
            node_id,
            active_only=False,
        )

        incoming_by_role = _role_counts(
            incoming
        )

        outgoing_by_role = _role_counts(
            outgoing
        )

        metadata = node.get(
            "metadata"
        )

        placeholder = bool(
            isinstance(
                metadata,
                Mapping,
            )
            and metadata.get(
                "lineage_placeholder",
                False,
            )
        )

        explicit_authority = bool(
            node.get(
                "authority",
                False,
            )
        )

        node_kind = str(
            node.get(
                "kind",
                "unknown",
            )
        )

        score = 0

        if explicit_authority:
            score += explicit_weight

        if node_kind.casefold() in authority_kinds:
            score += kind_weight

        score += _weighted_score(
            incoming_by_role,
            incoming_weights,
        )

        score += _weighted_score(
            outgoing_by_role,
            outgoing_weights,
        )

        structural = field_lookup.get(
            node_id,
            {},
        )

        structural_authority_mass = int(
            structural.get(
                "authority_mass",
                0,
            )
            or 0
        )

        score += min(
            100,
            structural_authority_mass
            // 4,
        )

        if placeholder:
            score -= placeholder_penalty

        score = max(
            0,
            score,
        )

        direct_authority_sources: set[
            str
        ] = set()

        authority_edges: list[
            str
        ] = []

        for edge in incoming:
            role = str(
                edge.get(
                    "role",
                    "generic",
                )
            )

            source_id = str(
                edge["source"]
            )

            source = index.node(
                source_id
            )

            if (
                role in governing_roles
                or source.get(
                    "authority",
                    False,
                )
            ):
                direct_authority_sources.add(
                    source_id
                )

                authority_edges.append(
                    str(
                        edge["id"]
                    )
                )

        authority_ancestors = index.traverse(
            node_id,
            direction="parents",
            roles=sorted(
                governing_roles
            ),
            max_depth=16,
            include_start=False,
        )

        ancestor_ids = sorted({
            str(
                item["id"]
            )
            for item in authority_ancestors
        })

        tier = _authority_tier(
            score,
            placeholder=placeholder,
            policy=policy,
        )

        tier_counts[
            tier
        ] += 1

        records.append({
            "id": node_id,
            "canonical_id": node.get(
                "canonical_id",
                node_id,
            ),
            "label": node.get(
                "label",
                node_id,
            ),
            "kind": node_kind,
            "explicit_authority": (
                explicit_authority
            ),
            "placeholder": placeholder,
            "authority_score": score,
            "authority_tier": tier,
            "direct_authority_sources": sorted(
                direct_authority_sources
            ),
            "authority_ancestors": ancestor_ids,
            "authority_edges": sorted(
                set(
                    authority_edges
                )
            ),
            "incoming_by_role": (
                incoming_by_role
            ),
            "outgoing_by_role": (
                outgoing_by_role
            ),
            "structural_authority_mass": (
                structural_authority_mass
            ),
            "provenance": deepcopy(
                node.get(
                    "provenance"
                )
            ),
        })

    records.sort(
        key=lambda item: (
            -item[
                "authority_score"
            ],
            item[
                "authority_tier"
            ],
            str(
                item["label"]
            ).casefold(),
            item["id"],
        )
    )

    for rank, record in enumerate(
        records,
        start=1,
    ):
        record[
            "authority_rank"
        ] = rank

    deterministic_core = {
        "schema": (
            "savant."
            "authority_index.v2"
        ),
        "source_runtime_hash": (
            index.deterministic_hash
        ),
        "source_lineage_hash": (
            index.source_lineage_hash
        ),
        "policy_id": policy.get(
            "id"
        ),
        "policy_version": policy.get(
            "version"
        ),
        "tier_counts": dict(
            sorted(
                tier_counts.items()
            )
        ),
        "records": records,
    }

    return {
        "schema": (
            "savant."
            "authority_index.v2"
        ),
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source": "runtime_graph",
        "source_runtime_hash": (
            index.deterministic_hash
        ),
        "source_lineage_hash": (
            index.source_lineage_hash
        ),
        "policy_id": policy.get(
            "id"
        ),
        "policy_version": policy.get(
            "version"
        ),
        "deterministic_hash": stable_hash(
            deterministic_core
        ),
        "count": len(
            records
        ),
        "tier_counts": dict(
            sorted(
                tier_counts.items()
            )
        ),
        "records": records,
    }


def write_authority_index(
    payload: Mapping[
        str,
        Any,
    ],
    output: Path = DEFAULT_OUTPUT,
) -> None:
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Project Savant authority "
            "from the functional-lineage "
            "runtime graph."
        )
    )

    parser.add_argument(
        "--graph",
        type=Path,
        default=DEFAULT_GRAPH,
    )

    parser.add_argument(
        "--fields",
        type=Path,
        default=DEFAULT_FIELDS,
    )

    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--node",
        default=None,
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    graph_payload = read_json(
        args.graph
    )

    fields_payload = read_json(
        args.fields,
        required=False,
    )

    policy = load_policy(
        args.policy
    )

    payload = compile_authority_index(
        graph_payload,
        structural_payload=(
            fields_payload
        ),
        policy=policy,
    )

    write_authority_index(
        payload,
        args.output,
    )

    report: dict[
        str,
        Any,
    ] = {
        "output": str(
            args.output
        ),
        "schema": payload[
            "schema"
        ],
        "count": payload[
            "count"
        ],
        "tier_counts": payload[
            "tier_counts"
        ],
        "source_runtime_hash": (
            payload[
                "source_runtime_hash"
            ]
        ),
        "source_lineage_hash": (
            payload[
                "source_lineage_hash"
            ]
        ),
        "deterministic_hash": (
            payload[
                "deterministic_hash"
            ]
        ),
    }

    if args.node:
        index = RuntimeGraphIndex(
            graph_payload
        )

        node_id = index.resolve_node_id(
            args.node
        )

        report[
            "record"
        ] = next(
            record
            for record
            in payload["records"]
            if record["id"]
            == node_id
        )

    print(
        json.dumps(
            report,
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
