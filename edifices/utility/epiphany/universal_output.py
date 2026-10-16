#!/usr/bin/env python3

from __future__ import annotations

import csv
import hashlib
from io import StringIO
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


schema = "savant://utility/epiphany/universal-output/1.0.0"
owner = "utility"
authority_effect = "none"
utility_level = "epiphany"
utility_ordinal = 4
universally_reusable = True

supported_formats = (
    "json",
    "jsonl",
    "text",
    "markdown",
    "csv",
)


class universal_output_error(RuntimeError):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def normalize(
    value: Any,
) -> Any:
    if hasattr(
        value,
        "projection",
    ):
        return normalize(
            value.projection()
        )

    if isinstance(
        value,
        Mapping,
    ):
        return {
            str(
                key
            ): normalize(
                nested
            )
            for key, nested
            in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
            frozenset,
        ),
    ):
        return [
            normalize(
                item
            )
            for item
            in value
        ]

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

    return str(
        value
    )


def as_records(
    value: Any,
) -> list[
    Mapping[str, Any]
]:
    normalized = normalize(
        value
    )

    if isinstance(
        normalized,
        Mapping,
    ):
        records = normalized.get(
            "records"
        )

        if isinstance(
            records,
            list,
        ) and all(
            isinstance(
                item,
                Mapping,
            )
            for item in records
        ):
            return [
                dict(
                    item
                )
                for item
                in records
            ]

        return [
            dict(
                normalized
            )
        ]

    if isinstance(
        normalized,
        list,
    ):
        projected: list[
            Mapping[str, Any]
        ] = []

        for ordinal, item in enumerate(
            normalized,
            1,
        ):
            if isinstance(
                item,
                Mapping,
            ):
                projected.append(
                    dict(
                        item
                    )
                )
            else:
                projected.append(
                    {
                        "ordinal": ordinal,
                        "value": item,
                    }
                )

        return projected

    return [
        {
            "value": normalized,
        }
    ]


def flatten(
    value: Any,
    prefix: str = "",
) -> dict[str, Any]:
    normalized = normalize(
        value
    )

    output: dict[
        str,
        Any,
    ] = {}

    if isinstance(
        normalized,
        Mapping,
    ):
        for key, nested in normalized.items():
            projected_key = (
                f"{prefix}.{key}"
                if prefix
                else str(
                    key
                )
            )

            if isinstance(
                nested,
                (
                    Mapping,
                    list,
                ),
            ):
                output.update(
                    flatten(
                        nested,
                        projected_key,
                    )
                )
            else:
                output[
                    projected_key
                ] = nested

        return output

    if isinstance(
        normalized,
        list,
    ):
        for ordinal, nested in enumerate(
            normalized
        ):
            projected_key = (
                f"{prefix}[{ordinal}]"
                if prefix
                else f"[{ordinal}]"
            )

            if isinstance(
                nested,
                (
                    Mapping,
                    list,
                ),
            ):
                output.update(
                    flatten(
                        nested,
                        projected_key,
                    )
                )
            else:
                output[
                    projected_key
                ] = nested

        return output

    output[
        prefix
        or "value"
    ] = normalized

    return output


def render_json(
    value: Any,
    *,
    pretty: bool = True,
) -> str:
    normalized = normalize(
        value
    )

    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        indent=(
            2
            if pretty
            else None
        ),
        separators=(
            None
            if pretty
            else (
                ",",
                ":",
            )
        ),
        default=str,
    ) + "\n"


def render_jsonl(
    value: Any,
) -> str:
    records = as_records(
        value
    )

    return "".join(
        canonical_json(
            record
        )
        + "\n"
        for record
        in records
    )


def scalar_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        bool,
    ):
        return (
            "true"
            if value
            else "false"
        )

    if isinstance(
        value,
        (
            str,
            int,
            float,
        ),
    ):
        return str(
            value
        )

    return canonical_json(
        normalize(
            value
        )
    )


def render_text(
    value: Any,
) -> str:
    normalized = normalize(
        value
    )

    if isinstance(
        normalized,
        str,
    ):
        return (
            normalized
            + (
                ""
                if normalized.endswith(
                    "\n"
                )
                else "\n"
            )
        )

    records = as_records(
        normalized
    )

    blocks: list[
        str
    ] = []

    for ordinal, record in enumerate(
        records,
        1,
    ):
        flattened = flatten(
            record
        )

        lines = [
            f"record {ordinal}"
        ]

        for key in sorted(
            flattened
        ):
            lines.append(
                f"{key}: "
                f"{scalar_text(flattened[key])}"
            )

        blocks.append(
            "\n".join(
                lines
            )
        )

    return (
        "\n\n".join(
            blocks
        )
        + "\n"
    )


def markdown_escape(
    value: Any,
) -> str:
    return (
        scalar_text(
            value
        )
        .replace(
            "\\",
            "\\\\",
        )
        .replace(
            "|",
            "\\|",
        )
        .replace(
            "\n",
            "<br>",
        )
    )


def render_markdown(
    value: Any,
) -> str:
    records = as_records(
        value
    )

    blocks: list[
        str
    ] = []

    for ordinal, record in enumerate(
        records,
        1,
    ):
        flattened = flatten(
            record
        )

        lines = [
            f"## record {ordinal}",
            "",
            "| field | value |",
            "|---|---|",
        ]

        for key in sorted(
            flattened
        ):
            lines.append(
                "| "
                + markdown_escape(
                    key
                )
                + " | "
                + markdown_escape(
                    flattened[
                        key
                    ]
                )
                + " |"
            )

        blocks.append(
            "\n".join(
                lines
            )
        )

    return (
        "\n\n".join(
            blocks
        )
        + "\n"
    )


def render_csv(
    value: Any,
) -> str:
    records = [
        flatten(
            record
        )
        for record
        in as_records(
            value
        )
    ]

    fields = sorted(
        {
            key
            for record
            in records
            for key
            in record
        }
    )

    buffer = StringIO()

    writer = csv.DictWriter(
        buffer,
        fieldnames=fields,
        extrasaction="ignore",
        lineterminator="\n",
    )

    writer.writeheader()

    for record in records:
        writer.writerow(
            {
                key:
                    scalar_text(
                        record.get(
                            key
                        )
                    )
                for key
                in fields
            }
        )

    return buffer.getvalue()


def render(
    value: Any,
    *,
    format: str = "json",
    pretty: bool = True,
) -> str:
    selected = (
        format
        .strip()
        .casefold()
    )

    if selected == "json":
        return render_json(
            value,
            pretty=pretty,
        )

    if selected == "jsonl":
        return render_jsonl(
            value
        )

    if selected == "text":
        return render_text(
            value
        )

    if selected in {
        "md",
        "markdown",
    }:
        return render_markdown(
            value
        )

    if selected == "csv":
        return render_csv(
            value
        )

    raise universal_output_error(
        "unsupported-output-format:"
        f"{format}"
    )


def write(
    value: Any,
    destination: str | Path,
    *,
    format: str = "json",
    pretty: bool = True,
) -> dict[str, Any]:
    output = Path(
        destination
    )

    encoded = render(
        value,
        format=format,
        pretty=pretty,
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        encoded,
        encoding="utf-8",
    )

    payload = encoded.encode(
        "utf-8"
    )

    return {
        "schema": schema,
        "owner": owner,
        "authority_effect":
            authority_effect,
        "utility_level":
            utility_level,
        "utility_ordinal":
            utility_ordinal,
        "universally_reusable":
            universally_reusable,
        "destination":
            str(
                output
            ),
        "format":
            format,
        "bytes":
            len(
                payload
            ),
        "sha256":
            hashlib.sha256(
                payload
            ).hexdigest(),
    }


def infer_format(
    destination: str | Path,
    default: str = "json",
) -> str:
    suffix = (
        Path(
            destination
        )
        .suffix
        .casefold()
    )

    mapping = {
        ".json": "json",
        ".jsonl": "jsonl",
        ".ndjson": "jsonl",
        ".txt": "text",
        ".md": "markdown",
        ".markdown": "markdown",
        ".csv": "csv",
    }

    return mapping.get(
        suffix,
        default,
    )


def selftest() -> dict[str, Any]:
    value = {
        "records": [
            {
                "name": "savant",
                "ordinal": 1,
            },
            {
                "name": "sieve",
                "ordinal": 2,
            },
        ]
    }

    json_first = render(
        value,
        format="json",
    )

    json_second = render(
        value,
        format="json",
    )

    jsonl = render(
        value,
        format="jsonl",
    )

    text = render(
        value,
        format="text",
    )

    markdown = render(
        value,
        format="markdown",
    )

    csv_value = render(
        value,
        format="csv",
    )

    checks = {
        "authority_none":
            authority_effect
            == "none",
        "level_04":
            utility_ordinal
            == 4,
        "universally_reusable":
            universally_reusable
            is True,
        "deterministic":
            json_first
            == json_second,
        "json":
            '"savant"'
            in json_first,
        "jsonl":
            len(
                [
                    line
                    for line
                    in jsonl.splitlines()
                    if line.strip()
                ]
            )
            == 2,
        "text":
            "name: savant"
            in text,
        "markdown":
            "| name | savant |"
            in markdown,
        "csv":
            "savant"
            in csv_value
            and "sieve"
            in csv_value,
        "format_inference":
            infer_format(
                "output.jsonl"
            )
            == "jsonl",
    }

    return {
        "schema":
            "savant://utility/epiphany/"
            "universal-output-selftest/1.0.0",
        "ok":
            all(
                checks.values()
            ),
        "checks":
            checks,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Project normalized Savant-compatible "
            "structures into selectable output formats."
        )
    )

    parser.add_argument(
        "input",
        nargs="?",
    )

    parser.add_argument(
        "output",
        nargs="?",
    )

    parser.add_argument(
        "--format",
        choices=supported_formats,
    )

    parser.add_argument(
        "--compact",
        action="store_true",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    arguments = parser.parse_args()

    if arguments.selftest:
        print(
            json.dumps(
                selftest(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )
        return 0

    if not arguments.input:
        raise universal_output_error(
            "input-required"
        )

    try:
        with open(
            arguments.input,
            "r",
            encoding="utf-8",
        ) as handle:
            value = json.load(
                handle
            )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise universal_output_error(
            "input-json-unavailable:"
            f"{arguments.input}"
        ) from exc

    selected_format = (
        arguments.format
        or (
            infer_format(
                arguments.output
            )
            if arguments.output
            else "json"
        )
    )

    if arguments.output:
        receipt = write(
            value,
            arguments.output,
            format=selected_format,
            pretty=not arguments.compact,
        )

        print(
            json.dumps(
                receipt,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )
    else:
        print(
            render(
                value,
                format=selected_format,
                pretty=not arguments.compact,
            ),
            end="",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
