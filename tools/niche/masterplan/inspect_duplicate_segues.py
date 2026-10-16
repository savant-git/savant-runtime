#!/usr/bin/env python3

from __future__ import annotations

import collections
import json
from pathlib import Path


ROOT = Path("/root/savant-runtime")

GRAPH = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)


def main() -> int:
    graph = json.loads(
        GRAPH.read_text(
            encoding="utf-8",
        )
    )

    groups = collections.defaultdict(list)

    for segue in graph.get("segues", []):
        key = (
            segue.get("type"),
            segue.get("source"),
            segue.get("target"),
        )

        groups[key].append(
            segue.get("id")
        )

    duplicates = {}

    for key, identifiers in sorted(groups.items()):
        if len(identifiers) > 1:
            duplicates["|".join(map(str, key))] = identifiers

    print(
        json.dumps(
            {
                "segue_count": len(graph.get("segues", [])),
                "semantic_relationship_count": len(groups),
                "duplicate_relationship_count": len(duplicates),
                "duplicates": duplicates,
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
