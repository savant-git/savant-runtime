#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path("/root/savant-runtime")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lexicon.kindred.discipline_engine import (
    DisciplineEngine,
    DisciplineError,
    KindredEdge,
)


class LegacyKindredBridgeError(ValueError):
    pass


SCALAR_FIELDS = {
    "parent": "relation:contained_by",
    "opposite": "relation:opposes",
}

LIST_FIELDS = {
    "children": "relation:contains",
    "related": "relation:related_to",
    "dependencies": "relation:depends_on",
    "dependents": "relation:required_by",
    "supersedes": "relation:supersedes",
    "superseded_by": "relation:superseded_by",
}

NESTED_FIELDS = {
    "lineage.parent": "relation:contained_by",
    "lineage.supersedes": "relation:supersedes",
    "lineage.superseded_by": "relation:superseded_by",
}

PROVENANCE_SOURCE_FIELDS = (
    "sources",
    "source",
    "created_from",
)


def _strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        value = value.strip()
        return (value,) if value else ()

    if isinstance(value, (list, tuple, set)):
        return tuple(
            sorted(
                {
                    str(item).strip()
                    for item in value
                    if str(item).strip()
                }
            )
        )

    return (str(value).strip(),)


def _nested(
    record: Mapping[str, Any],
    path: str,
) -> Any:
    value: Any = record

    for part in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)

    return value


def _subject_id(
    record: Mapping[str, Any],
    fallback: str | None = None,
) -> str:
    for field in (
        "id",
        "identity",
        "canonical_id",
        "graph_id",
    ):
        value = str(
            record.get(field, "")
        ).strip()

        if value:
            return value

    if fallback:
        return fallback

    raise LegacyKindredBridgeError(
        "record has no graph-addressable identity"
    )


class LegacyKindredBridge:
    """
    Compatibility projection for relationship-shaped legacy fields.

    This class never edits the source record. It only emits projected
    Kindred edges representing relationship semantics already present
    in the source.
    """

    def __init__(
        self,
        engine: DisciplineEngine | None = None,
    ) -> None:
        self.engine = (
            engine
            or DisciplineEngine()
        )

    def _edge(
        self,
        *,
        subject: str,
        relation: str,
        object_id: str,
        basis: str,
        source_field: str,
    ) -> KindredEdge:
        return KindredEdge(
            subject=subject,
            relation=relation,
            object=object_id,
            basis=basis,
            authority_state="projected",
            provenance={
                "projection": (
                    "legacy-kindred-bridge"
                ),
                "source_field": (
                    source_field
                ),
            },
            metadata={
                "compatibility": True,
                "source_field": source_field,
            },
        )

    def direct_edges(
        self,
        record: Mapping[str, Any],
        *,
        fallback_id: str | None = None,
        basis: str = "legacy-record",
    ) -> list[KindredEdge]:
        subject = _subject_id(
            record,
            fallback_id,
        )

        edges: list[KindredEdge] = []

        for field, relation in (
            SCALAR_FIELDS.items()
        ):
            for object_id in _strings(
                record.get(field)
            ):
                edges.append(
                    self._edge(
                        subject=subject,
                        relation=relation,
                        object_id=object_id,
                        basis=basis,
                        source_field=field,
                    )
                )

        for field, relation in (
            LIST_FIELDS.items()
        ):
            for object_id in _strings(
                record.get(field)
            ):
                edges.append(
                    self._edge(
                        subject=subject,
                        relation=relation,
                        object_id=object_id,
                        basis=basis,
                        source_field=field,
                    )
                )

        for path, relation in (
            NESTED_FIELDS.items()
        ):
            for object_id in _strings(
                _nested(
                    record,
                    path,
                )
            ):
                edges.append(
                    self._edge(
                        subject=subject,
                        relation=relation,
                        object_id=object_id,
                        basis=basis,
                        source_field=path,
                    )
                )

        provenance = record.get(
            "provenance"
        )

        if isinstance(
            provenance,
            Mapping,
        ):
            for field in (
                PROVENANCE_SOURCE_FIELDS
            ):
                for source in _strings(
                    provenance.get(field)
                ):
                    edges.append(
                        self._edge(
                            subject=subject,
                            relation=(
                                "relation:"
                                "sourced_from"
                            ),
                            object_id=(
                                f"source:{source}"
                            ),
                            basis=basis,
                            source_field=(
                                f"provenance.{field}"
                            ),
                        )
                    )

        lineage = record.get("lineage")

        if isinstance(lineage, list):
            for origin in _strings(
                lineage
            ):
                edges.append(
                    self._edge(
                        subject=subject,
                        relation=(
                            "relation:"
                            "derived_from"
                        ),
                        object_id=origin,
                        basis=basis,
                        source_field="lineage",
                    )
                )

        return edges

    def project(
        self,
        record: Mapping[str, Any],
        *,
        fallback_id: str | None = None,
        basis: str = "legacy-record",
        include_inverses: bool = True,
    ) -> dict[str, Any]:
        direct = self.direct_edges(
            record,
            fallback_id=fallback_id,
            basis=basis,
        )

        projected = (
            self.engine.project_edges(
                direct,
                include_inverses=(
                    include_inverses
                ),
            )
        )

        return {
            "schema": (
                "savant.kindred."
                "legacy-projection.v1"
            ),
            "authority_effect": "none",
            "mutation_effect": "none",
            "source_id": _subject_id(
                record,
                fallback_id,
            ),
            "direct_edge_count": len(
                direct
            ),
            "edge_count": len(
                projected
            ),
            "edges": projected,
        }


def _load_json(
    path: Path,
) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="kindred-legacy"
    )

    parser.add_argument(
        "path",
    )

    parser.add_argument(
        "--id",
        dest="fallback_id",
    )

    parser.add_argument(
        "--no-inverses",
        action="store_true",
    )

    args = parser.parse_args()

    try:
        path = Path(
            args.path
        ).expanduser().resolve()

        record = _load_json(path)

        if not isinstance(
            record,
            Mapping,
        ):
            raise LegacyKindredBridgeError(
                "input must be a JSON object"
            )

        bridge = LegacyKindredBridge()

        print(
            json.dumps(
                bridge.project(
                    record,
                    fallback_id=(
                        args.fallback_id
                    ),
                    basis=str(path),
                    include_inverses=(
                        not args.no_inverses
                    ),
                ),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
        )

        return 0

    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        DisciplineError,
        LegacyKindredBridgeError,
    ) as exc:
        print(
            json.dumps(
                {
                    "valid": False,
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
