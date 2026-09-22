#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path


TARGET = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/modus/segue/"
    "prodigals/coalesce/runtime/piece_engine.py"
)


REPLACEMENT = '''def lens(
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


'''


def find_function_line(
    lines: list[str],
    function_name: str,
) -> int:
    prefix = f"def {function_name}"

    for index, line in enumerate(
        lines
    ):
        if line.lstrip().startswith(
            prefix
        ):
            return index

    raise RuntimeError(
        f"{function_name} function not found"
    )


def main() -> int:
    source = TARGET.read_text(
        encoding="utf-8"
    )

    lines = source.splitlines(
        keepends=True
    )

    lens_start = find_function_line(
        lines,
        "lens",
    )

    relationship_start = (
        find_function_line(
            lines,
            "relationship_pairs",
        )
    )

    if relationship_start <= lens_start:
        raise RuntimeError(
            "invalid function ordering"
        )

    replacement_lines = (
        REPLACEMENT.splitlines(
            keepends=True
        )
    )

    updated_lines = (
        lines[:lens_start]
        + replacement_lines
        + lines[
            relationship_start:
        ]
    )

    TARGET.write_text(
        "".join(
            updated_lines
        ),
        encoding="utf-8",
    )

    print(
        "COALESCE OPTIONAL LENSES: corrected"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
