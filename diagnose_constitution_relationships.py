#!/usr/bin/env python3

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from runtime.constitution.bootstrap import load_authority


ROOT = Path(
    "/root/savant-runtime"
).resolve()


def json_safe(
    value: Any,
) -> Any:
    if isinstance(
        value,
        MappingProxyType,
    ):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        Mapping,
    ):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        tuple,
    ):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        list,
    ):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        set,
    ):
        return sorted(
            json_safe(item)
            for item in value
        )

    if isinstance(
        value,
        Path,
    ):
        return str(
            value
        )

    if value is None or isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    return repr(
        value
    )


def main() -> int:
    objects, kinds, schemas, relationships = (
        load_authority(
            ROOT
        )
    )

    problems: list[
        dict[str, Any]
    ] = []

    for obj in objects:
        primitives = json_safe(
            obj.to_primitives()
        )

        provenance = {}

        if isinstance(
            primitives,
            dict,
        ):
            candidate = primitives.get(
                "provenance",
                {},
            )

            if isinstance(
                candidate,
                dict,
            ):
                provenance = candidate

        for index, relation in enumerate(
            obj.relationships
        ):
            safe_relation = json_safe(
                relation
            )

            if not isinstance(
                relation,
                Mapping,
            ):
                problems.append(
                    {
                        "object_id": obj.id,
                        "kind": obj.kind,
                        "relationship_index": index,
                        "problem": (
                            "relationship_not_object"
                        ),
                        "relationship": safe_relation,
                        "provenance": provenance,
                    }
                )
                continue

            relation_type = (
                relation.get(
                    "type"
                )
            )

            if not str(
                relation_type
                or ""
            ).strip():
                problems.append(
                    {
                        "object_id": obj.id,
                        "kind": obj.kind,
                        "relationship_index": index,
                        "problem": (
                            "missing_relationship_type"
                        ),
                        "relationship": safe_relation,
                        "provenance": provenance,
                    }
                )
                continue

            relation_type_text = str(
                relation_type
            ).strip()

            if not relationships.contains(
                relation_type_text
            ):
                problems.append(
                    {
                        "object_id": obj.id,
                        "kind": obj.kind,
                        "relationship_index": index,
                        "problem": (
                            "unknown_relationship_type"
                        ),
                        "relationship": safe_relation,
                        "provenance": provenance,
                    }
                )

    report = {
        "root": str(
            ROOT
        ),
        "objects_loaded": len(
            objects
        ),
        "problem_count": len(
            problems
        ),
        "problems": problems,
    }

    print(
        json.dumps(
            json_safe(
                report
            ),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
    )

    return (
        1
        if problems
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
