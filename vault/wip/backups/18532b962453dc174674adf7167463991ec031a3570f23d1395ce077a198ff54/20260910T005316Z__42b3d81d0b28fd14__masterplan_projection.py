#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


schema_version = (
    "savant.niche.masterplan-projection.v1"
)

authority_effect = "none"

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
    }


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


def masterplan_projection() -> dict[
    str,
    Any,
]:
    (
        graph,
        source_sha256,
    ) = load_masterplan()

    graph_digest = sha256_bytes(
        canonical_json_bytes(
            graph
        )
    )

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "owner":
            "exile:niche",
        "projection":
            True,
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
        "metrics":
            graph_metrics(
                graph
            ),
        "graph":
            graph,
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
            "owner"
        )
        != "exile:niche"
    ):
        raise MasterplanProjectionError(
            "projection owner is invalid"
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
            "self-check",
        ),
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
                        str(exc),
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
