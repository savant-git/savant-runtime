#!/usr/bin/env python3

import json
from collections import Counter
from pathlib import Path


root = Path("/root/savant-runtime")

manifest_path = (
    root
    / "evolution/structure-migration/20260807T220514Z"
    / "migration-manifest.json"
)

data = json.loads(
    manifest_path.read_text(encoding="utf-8")
)

targets = (
    "vault/kindred-preview",
    "tools/sdump-enterprise",
    "vault/dimensions",
    "reports/niche",
    "authority/task-graph",
)


def normalize_current_path(value):
    raw = str(value or "")
    path = Path(raw)

    if path.is_absolute():
        try:
            return str(path.relative_to(root))
        except ValueError:
            return raw

    return raw.lstrip("./")


for target in targets:
    rows = []

    for artifact in data["artifacts"]:
        current_path = normalize_current_path(
            artifact.get("current_path")
        )

        if (
            current_path == target
            or current_path.startswith(target + "/")
        ):
            rows.append(artifact)

    print()
    print("=" * 80)
    print(target)
    print("count:", len(rows))

    for field in (
        "migration_action",
        "classification_rationale",
        "authority_state",
        "projection_state",
        "history_state",
        "semantic_owner",
        "owner_confidence",
        "rubric_owner",
        "shared_scope",
    ):
        counts = Counter(
            str(artifact.get(field))
            for artifact in rows
        )

        print(field + ":")

        for value, count in counts.most_common(12):
            print(
                f"  {count:>7}  {value[:180]}"
            )

    print("samples:")

    for artifact in rows[:3]:
        print(
            " ",
            artifact.get("current_path"),
        )
        print(
            "   canonical:",
            artifact.get("canonical_path"),
        )
        print(
            "   blockers:",
            artifact.get("blockers"),
        )
