#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
import math
import re
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


BASE = Path(__file__).resolve().parents[1]
PIECES_PATH = BASE / "registry" / "pieces.json"


Context = dict[str, Any]
Handler = Callable[[Context], Context]


def clone(value: Any) -> Any:
    return copy.deepcopy(value)


def records(context: Context) -> list[dict[str, Any]]:
    value = context.setdefault("records", [])

    if not isinstance(value, list):
        raise TypeError("context.records must be a list")

    return value


def artifacts(context: Context) -> dict[str, Any]:
    value = context.setdefault("artifacts", {})

    if not isinstance(value, dict):
        raise TypeError("context.artifacts must be an object")

    return value


def state(context: Context) -> dict[str, Any]:
    value = context.setdefault("state", {})

    if not isinstance(value, dict):
        raise TypeError("context.state must be an object")

    return value


def parameters(context: Context) -> dict[str, Any]:
    value = context.setdefault("parameters", {})

    if not isinstance(value, dict):
        raise TypeError("context.parameters must be an object")

    return value


def normalized_text(value: Any) -> str:
    return " ".join(
        str(value or "")
        .casefold()
        .split()
    )


def record_text(record: dict[str, Any]) -> str:
    return " ".join(
        normalized_text(
            record.get(key, "")
        )
        for key in (
            "title",
            "name",
            "label",
            "preview",
            "description",
            "summary",
            "body",
            "text",
            "content",
            "kind",
            "type",
            "status",
            "category",
            "domain",
            "owner",
        )
    )


def date_value(record: dict[str, Any]) -> str:
    for key in (
        "date",
        "occurred_at",
        "created_at",
        "timestamp",
    ):
        value = record.get(key)

        if value:
            return str(value)

    return ""


def parse_date(value: str) -> datetime | None:
    text = value.strip()

    if not text:
        return None

    candidates = [
        text,
        text.replace("Z", "+00:00"),
    ]

    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass

    match = re.match(
        r"^(\d{4})-(\d{2})-(\d{2})",
        text,
    )

    if match:
        try:
            return datetime(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
        except ValueError:
            return None

    return None


def canonical_record(
    record: dict[str, Any],
    ordinal: int,
) -> dict[str, Any]:
    out = clone(record)

    out["id"] = str(
        record.get("id")
        or f"record-{ordinal}"
    )

    out["title"] = str(
        record.get("title")
        or record.get("name")
        or record.get("label")
        or out["id"]
    )

    out["date"] = date_value(record)

    out["kind"] = str(
        record.get("kind")
        or record.get("type")
        or "record"
    )

    out["status"] = str(
        record.get("status")
        or "unknown"
    )

    out["category"] = str(
        record.get("category")
        or record.get("domain")
        or record.get("owner")
        or "general"
    )

    out["preview"] = str(
        record.get("preview")
        or record.get("description")
        or record.get("summary")
        or record.get("message")
        or ""
    )

    out["body"] = str(
        record.get("body")
        or record.get("text")
        or record.get("content")
        or out["preview"]
    )

    relationship_value = (
        record.get("relationships")
        or record.get("links")
        or record.get("dependencies")
        or []
    )

    out["relationships"] = (
        clone(relationship_value)
        if isinstance(
            relationship_value,
            list,
        )
        else []
    )

    return out


def temporal(
    name: str,
    context: Context,
) -> Context:
    rows = records(context)
    out = artifacts(context)
    params = parameters(context)

    if name == "date-normalizer":
        for row in rows:
            value = date_value(row)
            parsed = parse_date(value)

            if parsed:
                row["date"] = (
                    parsed.isoformat()
                )

        return context

    if name == "temporal-index":
        index = []

        for row in rows:
            value = date_value(row)
            parsed = parse_date(value)

            index.append(
                {
                    "id": row.get("id"),
                    "date": value,
                    "sortable": (
                        parsed.isoformat()
                        if parsed
                        else None
                    ),
                }
            )

        index.sort(
            key=lambda item: (
                item["sortable"] is None,
                item["sortable"] or "",
                str(item["id"]),
            )
        )

        out["temporal_index"] = index
        return context

    if name == "chronology-grouper":
        groups: dict[str, list[str]] = (
            defaultdict(list)
        )

        for row in rows:
            value = date_value(row)
            parsed = parse_date(value)
            key = (
                str(parsed.year)
                if parsed
                else "undated"
            )

            groups[key].append(
                str(row.get("id"))
            )

        out["chronology_groups"] = dict(
            sorted(groups.items())
        )

        return context

    if name == "density-map":
        density: Counter[str] = Counter()

        for row in rows:
            parsed = parse_date(
                date_value(row)
            )

            key = (
                f"{parsed.year:04d}-{parsed.month:02d}"
                if parsed
                else "undated"
            )

            density[key] += 1

        out["temporal_density"] = dict(
            sorted(density.items())
        )

        return context

    if name == "range-window":
        start = parse_date(
            str(params.get("start", ""))
        )

        end = parse_date(
            str(params.get("end", ""))
        )

        selected = []

        for row in rows:
            parsed = parse_date(
                date_value(row)
            )

            if parsed is None:
                continue

            if (
                start
                and parsed < start
            ):
                continue

            if (
                end
                and parsed > end
            ):
                continue

            selected.append(row)

        context["records"] = selected
        return context

    if name == "temporal-zoom":
        unit = str(
            params.get(
                "unit",
                "year",
            )
        )

        projection: dict[
            str,
            list[str],
        ] = defaultdict(list)

        for row in rows:
            parsed = parse_date(
                date_value(row)
            )

            if parsed is None:
                key = "undated"
            elif unit == "day":
                key = parsed.date().isoformat()
            elif unit == "month":
                key = (
                    f"{parsed.year:04d}-"
                    f"{parsed.month:02d}"
                )
            else:
                key = str(parsed.year)

            projection[key].append(
                str(row.get("id"))
            )

        out["temporal_zoom"] = dict(
            sorted(projection.items())
        )

        return context

    if name == "interval-resolver":
        intervals = []

        for row in rows:
            start_value = str(
                row.get("start")
                or date_value(row)
            )

            end_value = str(
                row.get("end")
                or start_value
            )

            start_date = parse_date(
                start_value
            )

            end_date = parse_date(
                end_value
            )

            intervals.append(
                {
                    "id": row.get("id"),
                    "start": (
                        start_date.isoformat()
                        if start_date
                        else None
                    ),
                    "end": (
                        end_date.isoformat()
                        if end_date
                        else None
                    ),
                }
            )

        out["intervals"] = intervals
        return context

    if name == "sequence-aligner":
        rows.sort(
            key=lambda row: (
                parse_date(
                    date_value(row)
                )
                or datetime.max,
                str(row.get("id")),
            )
        )

        for ordinal, row in enumerate(
            rows,
            start=1,
        ):
            row["_sequence"] = ordinal

        return context

    if name == "temporal-conflict-detector":
        seen: dict[
            tuple[str, str],
            list[str],
        ] = defaultdict(list)

        for row in rows:
            key = (
                str(row.get("id")),
                date_value(row),
            )

            seen[key].append(
                str(row.get("title", ""))
            )

        out["temporal_conflicts"] = [
            {
                "id": key[0],
                "date": key[1],
                "claims": values,
            }
            for key, values in seen.items()
            if len(values) > 1
        ]

        return context

    raise KeyError(name)


def record_ops(
    name: str,
    context: Context,
) -> Context:
    rows = records(context)
    out = artifacts(context)
    params = parameters(context)

    if name == "record-model":
        context["records"] = [
            canonical_record(
                row,
                ordinal,
            )
            for ordinal, row in enumerate(
                rows,
                start=1,
            )
        ]

        return context

    if name == "card-view":
        out["cards"] = [
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "preview": row.get(
                    "preview",
                    "",
                ),
                "date": date_value(row),
                "kind": row.get("kind"),
                "status": row.get("status"),
            }
            for row in rows
        ]

        return context

    if name == "detail-view":
        out["details"] = [
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "body": row.get(
                    "body",
                    row.get(
                        "content",
                        "",
                    ),
                ),
                "metadata": {
                    key: value
                    for key, value
                    in row.items()
                    if key not in (
                        "body",
                        "content",
                    )
                },
            }
            for row in rows
        ]

        return context

    if name == "provenance-view":
        out["provenance"] = [
            {
                "id": row.get("id"),
                "provenance": clone(
                    row.get("provenance")
                ),
            }
            for row in rows
        ]

        return context

    if name == "status-signals":
        out["status_counts"] = dict(
            Counter(
                str(
                    row.get(
                        "status",
                        "unknown",
                    )
                )
                for row in rows
            )
        )

        return context

    if name == "statistics":
        kinds = Counter(
            str(
                row.get(
                    "kind",
                    row.get(
                        "type",
                        "record",
                    ),
                )
            )
            for row in rows
        )

        out["statistics"] = {
            "record_count": len(rows),
            "kind_count": len(kinds),
            "kinds": dict(kinds),
        }

        return context

    if name == "record-normalizer":
        context["records"] = [
            canonical_record(
                row,
                ordinal,
            )
            for ordinal, row in enumerate(
                rows,
                start=1,
            )
        ]

        return context

    if name == "record-comparator":
        ids = params.get(
            "ids",
            [],
        )

        selected = [
            row
            for row in rows
            if row.get("id") in ids
        ]

        keys = sorted(
            {
                key
                for row in selected
                for key in row
            }
        )

        out["comparison"] = {
            key: [
                row.get(key)
                for row in selected
            ]
            for key in keys
        }

        return context

    if name == "record-inspector":
        out["record_inspection"] = [
            {
                "id": row.get("id"),
                "field_count": len(row),
                "fields": sorted(
                    row.keys()
                ),
                "has_provenance": (
                    "provenance" in row
                ),
                "relationship_count": len(
                    row.get(
                        "relationships",
                        [],
                    )
                    if isinstance(
                        row.get(
                            "relationships",
                            [],
                        ),
                        list,
                    )
                    else []
                ),
            }
            for row in rows
        ]

        return context

    raise KeyError(name)


def discovery(
    name: str,
    context: Context,
) -> Context:
    rows = records(context)
    out = artifacts(context)
    params = parameters(context)

    query = normalized_text(
        params.get("query", "")
    )

    terms = [
        term
        for term in query.split(" ")
        if term
    ]

    if name == "exact-search":
        context["records"] = [
            row
            for row in rows
            if not query
            or query in record_text(row)
        ]

        return context

    if name == "fuzzy-search":
        if not terms:
            return context

        scored = []

        for row in rows:
            text = record_text(row)
            points = sum(
                1
                for term in terms
                if term in text
            )

            if points:
                scored.append(
                    (
                        points,
                        row,
                    )
                )

        scored.sort(
            key=lambda item: (
                -item[0],
                str(
                    item[1].get(
                        "id",
                        "",
                    )
                ),
            )
        )

        context["records"] = [
            row
            for _, row in scored
        ]

        return context

    if name == "command-palette":
        out["commands"] = [
            {
                "id": "search",
                "accepts": "query",
            },
            {
                "id": "filter-kind",
                "accepts": "kind",
            },
            {
                "id": "filter-status",
                "accepts": "status",
            },
            {
                "id": "select",
                "accepts": "record-id",
            },
            {
                "id": "bookmark",
                "accepts": "record-id",
            },
            {
                "id": "compare",
                "accepts": "record-ids",
            },
            {
                "id": "export",
                "accepts": "projection",
            },
            {
                "id": "focus",
                "accepts": "record-id",
            },
            {
                "id": "reset",
                "accepts": "none",
            },
        ]

        return context

    if name == "smart-query":
        filters = params.get(
            "filters",
            {},
        )

        if not isinstance(
            filters,
            dict,
        ):
            raise TypeError(
                "parameters.filters must be an object"
            )

        selected = []

        for row in rows:
            if all(
                row.get(key) == value
                for key, value
                in filters.items()
            ):
                selected.append(row)

        context["records"] = selected
        return context

    if name == "relevance-ranker":
        ranked = []

        for row in rows:
            text = record_text(row)

            score = sum(
                (
                    9
                    if term in normalized_text(
                        row.get(
                            "title",
                            "",
                        )
                    )
                    else 3
                    if term in text
                    else 0
                )
                for term in terms
            )

            ranked.append(
                (
                    score,
                    row,
                )
            )

        ranked.sort(
            key=lambda item: (
                -item[0],
                str(
                    item[1].get(
                        "id",
                        "",
                    )
                ),
            )
        )

        out["relevance"] = {
            str(row.get("id")): score
            for score, row in ranked
        }

        context["records"] = [
            row
            for _, row in ranked
        ]

        return context

    if name == "result-highlighter":
        out["highlights"] = {
            str(row.get("id")): [
                term
                for term in terms
                if term in record_text(row)
            ]
            for row in rows
        }

        return context

    if name == "facet-search":
        facet = str(
            params.get(
                "facet",
                "kind",
            )
        )

        out["facets"] = dict(
            Counter(
                str(
                    row.get(
                        facet,
                        "unknown",
                    )
                )
                for row in rows
            )
        )

        return context

    if name == "query-history":
        history = state(
            context
        ).setdefault(
            "query_history",
            [],
        )

        if query:
            history.append(query)

        out["query_history"] = clone(
            history
        )

        return context

    if name == "discovery-suggester":
        tokens: Counter[str] = Counter()

        for row in rows:
            tokens.update(
                token
                for token in re.findall(
                    r"[a-z0-9_-]+",
                    record_text(row),
                )
                if len(token) >= 3
            )

        out["suggestions"] = [
            token
            for token, _
            in tokens.most_common(9)
        ]

        return context

    raise KeyError(name)


def lens(
    name: str,
    context: Context,
) -> Context:
    rows = records(context)
    params = parameters(context)

    field_by_name = {
        "category-lens": "category",
        "kind-lens": "kind",
        "status-lens": "status",
    }

    if name in field_by_name:
        field = field_by_name[name]

        lens_values = params.get(
            "lens_values",
            {},
        )

        if not isinstance(
            lens_values,
            dict,
        ):
            raise TypeError(
                "parameters.lens_values must be an object"
            )

        value = lens_values.get(
            field
        )

        if value is None:
            return context

        context["records"] = [
            row
            for row in rows
            if row.get(field) == value
        ]

        return context

    if name == "conflict-lens":
        if not bool(
            params.get(
                "conflicts_only",
                False,
            )
        ):
            return context

        context["records"] = [
            row
            for row in rows
            if (
                row.get("conflict")
                or row.get("conflicts")
                or row.get("status")
                == "conflict"
            )
        ]

        return context

    if name == "bookmark-lens":
        if not bool(
            params.get(
                "bookmarks_only",
                False,
            )
        ):
            return context

        marked = set(
            state(context).get(
                "bookmarks",
                [],
            )
        )

        context["records"] = [
            row
            for row in rows
            if row.get("id") in marked
        ]

        return context

    if name == "focus-lens":
        focus_id = params.get(
            "focus_id"
        )

        if focus_id is None:
            return context

        context["records"] = [
            row
            for row in rows
            if row.get("id") == focus_id
        ]

        return context

    if name == "provenance-lens":
        if not bool(
            params.get(
                "provenance_only",
                False,
            )
        ):
            return context

        context["records"] = [
            row
            for row in rows
            if row.get("provenance")
        ]

        return context

    if name == "relationship-lens":
        if not bool(
            params.get(
                "relationships_only",
                False,
            )
        ):
            return context

        context["records"] = [
            row
            for row in rows
            if row.get(
                "relationships"
            )
        ]

        return context

    if name == "confidence-lens":
        if (
            "minimum_confidence"
            not in params
        ):
            return context

        minimum = float(
            params[
                "minimum_confidence"
            ]
        )

        context["records"] = [
            row
            for row in rows
            if float(
                row.get(
                    "confidence",
                    0,
                )
                or 0
            )
            >= minimum
        ]

        return context

    raise KeyError(name)


def relationship_pairs(
    rows: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    pairs = []

    known = {
        str(row.get("id"))
        for row in rows
    }

    for row in rows:
        source = str(
            row.get("id")
        )

        values = row.get(
            "relationships",
            [],
        )

        if not isinstance(
            values,
            list,
        ):
            continue

        for item in values:
            if isinstance(item, str):
                target = item
            elif isinstance(item, dict):
                target = str(
                    item.get(
                        "target",
                        "",
                    )
                )
            else:
                continue

            if (
                target
                and target in known
            ):
                pairs.append(
                    (
                        source,
                        target,
                    )
                )

    return pairs


def gridd(
    name: str,
    context: Context,
) -> Context:
    rows = records(context)
    out = artifacts(context)
    params = parameters(context)

    pairs = relationship_pairs(
        rows
    )

    adjacency: dict[
        str,
        set[str],
    ] = defaultdict(set)

    for source, target in pairs:
        adjacency[source].add(
            target
        )

        adjacency[target].add(
            source
        )

    if name == "gridd-builder":
        out["gridd"] = {
            "nodes": [
                str(row.get("id"))
                for row in rows
            ],
            "edges": [
                {
                    "source": source,
                    "target": target,
                }
                for source, target
                in pairs
            ],
        }

        return context

    if name == "relation-mapper":
        out["relationship_map"] = {
            key: sorted(values)
            for key, values
            in adjacency.items()
        }

        return context

    if name == "pathfinder":
        start_id = str(
            params.get(
                "start",
                "",
            )
        )

        target_id = str(
            params.get(
                "target",
                "",
            )
        )

        queue = deque(
            [
                (
                    start_id,
                    [start_id],
                )
            ]
        )

        visited = {
            start_id
        }

        found = []

        while queue:
            current, path = (
                queue.popleft()
            )

            if current == target_id:
                found = path
                break

            for next_id in sorted(
                adjacency.get(
                    current,
                    set(),
                )
            ):
                if next_id in visited:
                    continue

                visited.add(
                    next_id
                )

                queue.append(
                    (
                        next_id,
                        path
                        + [next_id],
                    )
                )

        out["path"] = found
        return context

    if name == "neighborhood-view":
        center = str(
            params.get(
                "id",
                "",
            )
        )

        out["neighborhood"] = {
            "center": center,
            "neighbors": sorted(
                adjacency.get(
                    center,
                    set(),
                )
            ),
        }

        return context

    if name == "gridd-view":
        out["gridd_view"] = [
            {
                "id": node,
                "degree": len(
                    adjacency.get(
                        node,
                        set(),
                    )
                ),
                "neighbors": sorted(
                    adjacency.get(
                        node,
                        set(),
                    )
                ),
            }
            for node in sorted(
                {
                    str(
                        row.get("id")
                    )
                    for row in rows
                }
            )
        ]

        return context

    if name == "gridd-export":
        out["gridd_export"] = {
            "nodes": [
                {
                    "id": row.get("id"),
                    "title": row.get(
                        "title",
                        row.get("name"),
                    ),
                }
                for row in rows
            ],
            "edges": [
                {
                    "source": source,
                    "target": target,
                }
                for source, target
                in pairs
            ],
        }

        return context

    if name == "centrality-analyzer":
        out["centrality"] = {
            node: len(
                neighbors
            )
            for node, neighbors
            in adjacency.items()
        }

        return context

    if name == "cluster-view":
        remaining = set(
            str(row.get("id"))
            for row in rows
        )

        clusters = []

        while remaining:
            start_id = sorted(
                remaining
            )[0]

            queue = deque(
                [start_id]
            )

            cluster = set()

            while queue:
                node = queue.popleft()

                if node in cluster:
                    continue

                cluster.add(node)

                for neighbor in adjacency.get(
                    node,
                    set(),
                ):
                    if neighbor not in cluster:
                        queue.append(
                            neighbor
                        )

            remaining -= cluster

            clusters.append(
                sorted(cluster)
            )

        out["clusters"] = clusters
        return context

    if name == "relationship-inspector":
        out["relationship_inspection"] = {
            "node_count": len(rows),
            "edge_count": len(pairs),
            "isolated": sorted(
                str(row.get("id"))
                for row in rows
                if not adjacency.get(
                    str(row.get("id"))
                )
            ),
        }

        return context

    raise KeyError(name)


def workspace(
    name: str,
    context: Context,
) -> Context:
    rows = records(context)
    out = artifacts(context)
    params = parameters(context)
    runtime_state = state(context)

    if name == "compare":
        ids = set(
            params.get(
                "ids",
                [],
            )
        )

        out["workspace_compare"] = [
            clone(row)
            for row in rows
            if row.get("id") in ids
        ]

        return context

    if name == "notes":
        notes = runtime_state.setdefault(
            "notes",
            {},
        )

        record_id = params.get(
            "id"
        )

        if (
            record_id
            and "note" in params
        ):
            notes[str(record_id)] = str(
                params["note"]
            )

        out["notes"] = clone(
            notes
        )

        return context

    if name == "bookmarks":
        bookmarks = set(
            runtime_state.get(
                "bookmarks",
                [],
            )
        )

        record_id = params.get(
            "id"
        )

        if record_id:
            if record_id in bookmarks:
                bookmarks.remove(
                    record_id
                )
            else:
                bookmarks.add(
                    record_id
                )

        runtime_state["bookmarks"] = sorted(
            bookmarks
        )

        return context

    if name == "deep-links":
        out["deep_links"] = {
            str(row.get("id")): (
                "#record="
                + str(row.get("id"))
            )
            for row in rows
        }

        return context

    if name == "clipboard":
        ids = set(
            params.get(
                "ids",
                [],
            )
        )

        runtime_state["clipboard"] = [
            clone(row)
            for row in rows
            if not ids
            or row.get("id") in ids
        ]

        return context

    if name == "export-print":
        out["print_projection"] = [
            {
                "id": row.get("id"),
                "title": row.get(
                    "title",
                    "",
                ),
                "body": row.get(
                    "body",
                    row.get(
                        "preview",
                        "",
                    ),
                ),
            }
            for row in rows
        ]

        return context

    if name == "workspace-history":
        history = runtime_state.setdefault(
            "history",
            [],
        )

        history.append(
            {
                "record_count": len(rows),
                "query": params.get(
                    "query"
                ),
            }
        )

        out["workspace_history"] = clone(
            history
        )

        return context

    if name == "selection-set":
        ids = set(
            params.get(
                "ids",
                [],
            )
        )

        runtime_state["selection"] = sorted(
            ids
        )

        return context

    if name == "saved-view":
        key = str(
            params.get(
                "name",
                "default",
            )
        )

        views = runtime_state.setdefault(
            "saved_views",
            {},
        )

        views[key] = {
            "parameters": clone(
                params
            ),
            "record_ids": [
                row.get("id")
                for row in rows
            ],
        }

        return context

    raise KeyError(name)


def narrative(
    name: str,
    context: Context,
) -> Context:
    rows = records(context)
    out = artifacts(context)
    params = parameters(context)

    ordered = sorted(
        rows,
        key=lambda row: (
            parse_date(
                date_value(row)
            )
            or datetime.max,
            str(row.get("id")),
        ),
    )

    if name == "story-mode":
        out["story"] = [
            {
                "id": row.get("id"),
                "title": row.get(
                    "title",
                    "",
                ),
                "date": date_value(row),
            }
            for row in ordered
        ]

        return context

    if name == "stepper":
        out["steps"] = [
            {
                "step": ordinal,
                "id": row.get("id"),
            }
            for ordinal, row in enumerate(
                ordered,
                start=1,
            )
        ]

        return context

    if name == "spotlight":
        selected_id = params.get(
            "id"
        )

        out["spotlight"] = next(
            (
                clone(row)
                for row in rows
                if row.get("id")
                == selected_id
            ),
            None,
        )

        return context

    if name == "milestones":
        out["milestones"] = [
            clone(row)
            for row in ordered
            if (
                row.get("milestone")
                or row.get("kind")
                == "milestone"
            )
        ]

        return context

    if name == "chapter-rail":
        chapters: dict[
            str,
            list[str],
        ] = defaultdict(list)

        for row in ordered:
            parsed = parse_date(
                date_value(row)
            )

            chapter = (
                str(parsed.year)
                if parsed
                else str(
                    row.get(
                        "category",
                        "undated",
                    )
                )
            )

            chapters[chapter].append(
                str(row.get("id"))
            )

        out["chapters"] = dict(
            chapters
        )

        return context

    if name == "intel-panel":
        selected_id = params.get(
            "id"
        )

        out["intel"] = next(
            (
                {
                    "id": row.get("id"),
                    "title": row.get(
                        "title",
                        "",
                    ),
                    "preview": row.get(
                        "preview",
                        "",
                    ),
                    "status": row.get(
                        "status",
                    ),
                    "kind": row.get(
                        "kind",
                    ),
                }
                for row in rows
                if row.get("id")
                == selected_id
            ),
            None,
        )

        return context

    if name == "branch-traversal":
        out["branches"] = {
            str(row.get("id")): [
                item.get(
                    "target"
                )
                if isinstance(
                    item,
                    dict,
                )
                else item
                for item in row.get(
                    "relationships",
                    [],
                )
                if isinstance(
                    row.get(
                        "relationships",
                        [],
                    ),
                    list,
                )
            ]
            for row in rows
        }

        return context

    if name == "narrative-path":
        out["narrative_path"] = [
            str(row.get("id"))
            for row in ordered
        ]

        return context

    if name == "presentation-sequence":
        out["presentation"] = [
            {
                "ordinal": ordinal,
                "id": row.get("id"),
                "headline": row.get(
                    "title",
                    "",
                ),
                "support": row.get(
                    "preview",
                    "",
                ),
            }
            for ordinal, row in enumerate(
                ordered,
                start=1,
            )
        ]

        return context

    raise KeyError(name)


def shell(
    name: str,
    context: Context,
) -> Context:
    out = artifacts(context)
    params = parameters(context)

    if name == "responsive-shell":
        out["responsive_shell"] = {
            "adaptive": True,
            "regions": [
                "header",
                "toolbar",
                "rail",
                "content",
                "intel",
                "drawer",
                "dock",
                "status",
                "extension",
            ],
        }

        return context

    if name == "mobile-dock":
        out["mobile_dock"] = [
            "search",
            "lens",
            "navigate",
            "select",
            "bookmark",
            "compare",
            "story",
            "export",
            "more",
        ]

        return context

    if name == "mobile-sheet":
        out["mobile_sheet"] = {
            "open": bool(
                params.get(
                    "open",
                    False,
                )
            ),
            "content": params.get(
                "content"
            ),
        }

        return context

    if name == "keyboard-router":
        out["keyboard"] = {
            "/": "search",
            "Escape": "close",
            "d": "density",
            "j": "next",
            "k": "previous",
            "b": "bookmark",
            "c": "compare",
            "f": "focus",
            "x": "export",
        }

        return context

    if name == "view-modes":
        out["view_modes"] = [
            "chronology",
            "cards",
            "gridd",
            "table",
            "story",
            "compare",
            "provenance",
            "status",
            "compact",
        ]

        return context

    if name == "accessibility":
        out["accessibility"] = {
            "keyboard": True,
            "reduced_motion": True,
            "semantic_regions": True,
            "focus_management": True,
            "screen_reader_labels": True,
            "high_contrast_ready": True,
            "non_pointer_operation": True,
            "logical_heading_order": True,
            "state_announcements": True,
        }

        return context

    if name == "command-router":
        out["command_router"] = {
            str(
                params.get(
                    "command",
                    "",
                )
            ): clone(
                params.get(
                    "arguments",
                    {},
                )
            )
        }

        return context

    if name == "panel-manager":
        panels = state(
            context
        ).setdefault(
            "panels",
            {},
        )

        panel = str(
            params.get(
                "panel",
                "main",
            )
        )

        panels[panel] = bool(
            params.get(
                "open",
                True,
            )
        )

        return context

    if name == "layout-projector":
        out["layout"] = {
            "recipe": params.get(
                "layout",
                "adaptive",
            ),
            "regions": clone(
                params.get(
                    "regions",
                    [],
                )
            ),
        }

        return context

    raise KeyError(name)


def substrate(
    name: str,
    context: Context,
) -> Context:
    out = artifacts(context)
    params = parameters(context)
    runtime_state = state(context)

    if name == "state-store":
        out["state"] = clone(
            runtime_state
        )
        return context

    if name == "persistence":
        out["persistence"] = {
            "serializable": True,
            "payload": clone(
                runtime_state
            ),
        }
        return context

    if name == "schema-guard":
        errors = []

        for ordinal, row in enumerate(
            records(context),
            start=1,
        ):
            if not isinstance(
                row,
                dict,
            ):
                errors.append(
                    {
                        "ordinal": ordinal,
                        "error": (
                            "record_not_object"
                        ),
                    }
                )

        out["schema_errors"] = errors
        return context

    if name == "plugin-sear":
        out["plugins"] = clone(
            params.get(
                "plugins",
                [],
            )
        )
        return context

    if name == "dependency-loader":
        dependencies = clone(
            params.get(
                "dependencies",
                [],
            )
        )

        out["dependencies"] = {
            "requested": dependencies,
            "loaded": [],
            "fallback_active": bool(
                dependencies
            ),
        }

        return context

    if name == "recipe-compiler":
        out["recipe_compilation"] = {
            "piece_ids": clone(
                params.get(
                    "piece_ids",
                    [],
                )
            ),
            "composition": "reference",
        }

        return context

    if name == "capability-negotiator":
        requested = set(
            params.get(
                "requested",
                [],
            )
        )

        available = set(
            params.get(
                "available",
                [],
            )
        )

        out["capabilities"] = {
            "accepted": sorted(
                requested
                & available
            ),
            "missing": sorted(
                requested
                - available
            ),
        }

        return context

    if name == "composition-digest":
        payload = json.dumps(
            {
                "records": records(
                    context
                ),
                "state": runtime_state,
                "parameters": params,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        value = 0

        for character in payload:
            value = (
                value * 33
                + ord(character)
            ) % (
                9 ** 9
            )

        out["composition_digest"] = (
            f"{value:09d}"
        )

        return context

    if name == "extension-host":
        out["extensions"] = {
            "registered": clone(
                params.get(
                    "extensions",
                    [],
                )
            ),
            "authority_effect": (
                "none"
            ),
        }

        return context

    raise KeyError(name)


RUNNERS: dict[
    str,
    Callable[
        [str, Context],
        Context,
    ],
] = {
    "temporal": temporal,
    "record": record_ops,
    "discovery": discovery,
    "lens": lens,
    "gridd": gridd,
    "workspace": workspace,
    "narrative": narrative,
    "shell": shell,
    "substrate": substrate,
}


def load_piece_registry() -> dict[
    str,
    dict[str, Any],
]:
    document = json.loads(
        PIECES_PATH.read_text(
            encoding="utf-8"
        )
    )

    pieces = {
        piece["id"]: piece
        for piece
        in document["pieces"]
    }

    if len(pieces) != 81:
        raise RuntimeError(
            "Coalesce piece registry must contain eighty-one pieces"
        )

    return pieces


def resolve_piece(
    identity: str,
    piece_registry: dict[
        str,
        dict[str, Any],
    ],
) -> dict[str, Any]:
    if identity in piece_registry:
        return piece_registry[
            identity
        ]

    matches = [
        piece
        for piece
        in piece_registry.values()
        if piece.get(
            "canonical_name"
        )
        == identity
    ]

    if len(matches) != 1:
        raise KeyError(
            f"unknown Coalesce piece: {identity}"
        )

    return matches[0]


def execute_piece(
    identity: str,
    context: Context,
) -> Context:
    registry = load_piece_registry()

    piece = resolve_piece(
        identity,
        registry,
    )

    service = str(
        piece["service"]
    )

    name = str(
        piece["canonical_name"]
    )

    runner = RUNNERS.get(
        service
    )

    if runner is None:
        raise KeyError(
            f"unknown Coalesce service: {service}"
        )

    working = clone(
        context
    )

    working.setdefault(
        "records",
        [],
    )

    working.setdefault(
        "state",
        {},
    )

    working.setdefault(
        "parameters",
        {},
    )

    working.setdefault(
        "artifacts",
        {},
    )

    working = runner(
        name,
        working,
    )

    trace = working.setdefault(
        "trace",
        [],
    )

    trace.append(
        {
            "piece_id": piece["id"],
            "service": service,
            "piece": name,
            "moods": clone(
                piece.get(
                    "mood_bindings",
                    [],
                )
            ),
            "authority_effect": (
                "none"
            ),
        }
    )

    return working


def execute_pieces(
    identities: list[str],
    context: Context,
) -> Context:
    count = len(
        identities
    )

    if not (
        count == 3
        or (
            count > 0
            and count % 9 == 0
        )
    ):
        raise RuntimeError(
            "Coalesce composition must contain three pieces or a multiple of nine"
        )

    working = clone(
        context
    )

    for identity in identities:
        working = execute_piece(
            identity,
            working,
        )

    return working


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="coalesce-piece-engine"
    )

    parser.add_argument(
        "piece",
    )

    parser.add_argument(
        "--context",
        default="{}",
    )

    args = parser.parse_args()

    context = json.loads(
        args.context
    )

    result = execute_piece(
        args.piece,
        context,
    )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
