#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence


runtime_root = Path(
    "/root/savant-runtime/tools/extr-enterprise/runtime"
)

if str(runtime_root) not in sys.path:
    sys.path.insert(
        0,
        str(runtime_root),
    )

from importer import import_path
from partition import (
    classify_rows,
    datrix_projection,
    load_runtime_profile_file,
    runtime_profile,
)
from pass_engine import (
    pass_definition,
    pass_engine,
)


schema = "savant://runtime/extr/engine/1.0.0"
owner = "extr"
authority_effect = "none"

default_pass_config = Path(
    "/root/savant-runtime/tools/extr-enterprise/config/passes.json"
)


class engine_error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class run_request:
    inputs: tuple[Path, ...]
    categories: Path
    output: Path
    passes: tuple[str, ...]
    pass_config: Path

    def projection(self) -> dict[str, Any]:
        return {
            "inputs": [
                str(path)
                for path in self.inputs
            ],
            "categories":
                str(self.categories),
            "output":
                str(self.output),
            "passes":
                list(self.passes),
            "pass_config":
                str(self.pass_config),
        }


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
        ).encode("utf-8")
    ).hexdigest()


def atomic_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=str(path.parent),
        )
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                value,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                default=str,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            path,
        )

    finally:
        temporary.unlink(
            missing_ok=True
        )


def atomic_jsonl(
    path: Path,
    rows: Iterable[
        Mapping[str, Any]
    ],
) -> int:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=str(path.parent),
        )
    )

    temporary = Path(
        temporary_name
    )

    count = 0

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            for row in rows:
                handle.write(
                    canonical_json(
                        row
                    )
                )
                handle.write("\n")
                count += 1

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            path,
        )

    finally:
        temporary.unlink(
            missing_ok=True
        )

    return count


def load_pass_definitions(
    path: Path,
) -> tuple[
    pass_definition,
    ...,
]:
    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    raw_passes = payload.get(
        "passes",
        [],
    )

    if not isinstance(
        raw_passes,
        list,
    ):
        raise engine_error(
            "pass configuration requires "
            "a passes array"
        )

    definitions = []

    for raw in raw_passes:
        if not isinstance(
            raw,
            Mapping,
        ):
            raise engine_error(
                "pass definition must "
                "be an object"
            )

        pass_id = str(
            raw.get(
                "id",
                "",
            )
        ).strip()

        purpose = str(
            raw.get(
                "purpose",
                "",
            )
        ).strip()

        if (
            not pass_id
            or not purpose
        ):
            raise engine_error(
                "pass definition requires "
                "id and purpose"
            )

        definitions.append(
            pass_definition(
                id=pass_id,
                purpose=purpose,
            )
        )

    return tuple(
        definitions
    )


def content_text(
    record: Mapping[str, Any],
) -> str:
    content = record.get(
        "content"
    )

    if isinstance(
        content,
        str,
    ):
        return content

    if content is None:
        return ""

    return canonical_json(
        content
    )


def normalized_record(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    projected = dict(
        record
    )

    projected["text"] = (
        content_text(record)
    )

    projected[
        "extr_engine"
    ] = {
        "schema": schema,
        "owner": owner,
        "authority_effect":
            authority_effect,
        "authoritative":
            False,
        "source_record_digest":
            digest(record),
    }

    return projected


def ingest_inputs(
    paths: Sequence[Path],
) -> list[
    dict[str, Any]
]:
    rows: list[
        dict[str, Any]
    ] = []

    seen_records: set[
        str
    ] = set()

    for path in paths:
        for record in import_path(
            path
        ):
            normalized = (
                normalized_record(
                    record
                )
            )

            record_digest = digest(
                normalized
            )

            if (
                record_digest
                in seen_records
            ):
                continue

            seen_records.add(
                record_digest
            )

            normalized[
                "extr_engine"
            ][
                "record_digest"
            ] = record_digest

            rows.append(
                normalized
            )

    return rows


def identity_pass(
    value: Any,
    context: Mapping[
        str,
        Any,
    ],
) -> Any:
    return value


def normalize_pass(
    value: Any,
    context: Mapping[
        str,
        Any,
    ],
) -> Any:
    if not isinstance(
        value,
        list,
    ):
        return value

    projected = []

    for item in value:
        if not isinstance(
            item,
            Mapping,
        ):
            projected.append(
                item
            )
            continue

        row = dict(item)

        text = row.get(
            "text"
        )

        if isinstance(
            text,
            str,
        ):
            row[
                "normalized_text"
            ] = " ".join(
                text.split()
            )

        projected.append(
            row
        )

    return projected


def deduplicate_pass(
    value: Any,
    context: Mapping[
        str,
        Any,
    ],
) -> Any:
    if not isinstance(
        value,
        list,
    ):
        return value

    seen: dict[
        str,
        int,
    ] = {}

    projected = []

    for item in value:
        item_digest = digest(
            item
        )

        if item_digest in seen:
            continue

        seen[
            item_digest
        ] = len(projected)

        projected.append(
            item
        )

    return projected


def lineage_pass(
    value: Any,
    context: Mapping[
        str,
        Any,
    ],
) -> Any:
    if not isinstance(
        value,
        list,
    ):
        return value

    projected = []

    for item in value:
        if not isinstance(
            item,
            Mapping,
        ):
            projected.append(
                item
            )
            continue

        row = dict(item)

        engine_projection = dict(
            row.get(
                "extr_engine",
                {},
            )
        )

        engine_projection[
            "lineage_digest"
        ] = digest(
            {
                "source":
                    row.get(
                        "source"
                    ),
                "lineage":
                    row.get(
                        "lineage"
                    ),
                "content":
                    row.get(
                        "content"
                    ),
            }
        )

        row[
            "extr_engine"
        ] = engine_projection

        projected.append(
            row
        )

    return projected


def quality_pass(
    value: Any,
    context: Mapping[
        str,
        Any,
    ],
) -> Any:
    if not isinstance(
        value,
        list,
    ):
        return value

    projected = []

    for item in value:
        if not isinstance(
            item,
            Mapping,
        ):
            projected.append(
                item
            )
            continue

        row = dict(item)

        text = str(
            row.get(
                "text",
                "",
            )
        )

        nonspace = sum(
            1
            for character in text
            if not character.isspace()
        )

        printable = sum(
            1
            for character in text
            if character.isprintable()
        )

        total = max(
            len(text),
            1,
        )

        row[
            "extr_quality"
        ] = {
            "empty":
                nonspace == 0,
            "characters":
                len(text),
            "nonspace_characters":
                nonspace,
            "printable_ratio":
                round(
                    printable
                    / total,
                    6,
                ),
        }

        projected.append(
            row
        )

    return projected


def category_pass(
    value: Any,
    context: Mapping[
        str,
        Any,
    ],
) -> Any:
    if not isinstance(
        value,
        list,
    ):
        raise engine_error(
            "category pass requires "
            "a record list"
        )

    profile = context.get(
        "runtime_profile"
    )

    if not isinstance(
        profile,
        runtime_profile,
    ):
        raise engine_error(
            "category pass requires "
            "runtime_profile"
        )

    return classify_rows(
        [
            dict(item)
            for item in value
            if isinstance(
                item,
                Mapping,
            )
        ],
        profile,
    )


def graph_pass(
    value: Any,
    context: Mapping[
        str,
        Any,
    ],
) -> Any:
    if not isinstance(
        value,
        list,
    ):
        return value

    projected = []

    for item in value:
        if not isinstance(
            item,
            Mapping,
        ):
            continue

        row = dict(item)

        if "extr_partition" in row:
            row[
                "extr_datrix_projection"
            ] = datrix_projection(
                row
            )

        projected.append(
            row
        )

    return projected


def project_pass(
    value: Any,
    context: Mapping[
        str,
        Any,
    ],
) -> Any:
    return value


def register_builtin_passes(
    engine: pass_engine,
) -> None:
    deterministic_handlers = {
        "ingest":
            identity_pass,
        "structure":
            identity_pass,
        "segment":
            identity_pass,
        "normalize":
            normalize_pass,
        "deduplicate":
            deduplicate_pass,
        "identity":
            identity_pass,
        "provenance":
            lineage_pass,
        "language":
            identity_pass,
        "temporal":
            identity_pass,
        "context":
            identity_pass,
        "confidence":
            identity_pass,
        "catchall":
            identity_pass,
        "chronology":
            identity_pass,
        "edifice":
            identity_pass,
        "quality":
            quality_pass,
        "privacy":
            identity_pass,
        "authority":
            identity_pass,
        "lineage":
            lineage_pass,
        "graph":
            graph_pass,
        "index":
            identity_pass,
        "category":
            category_pass,
        "organize":
            identity_pass,
        "recover":
            identity_pass,
        "validate":
            identity_pass,
        "project":
            project_pass,
    }

    for (
        pass_id,
        handler,
    ) in deterministic_handlers.items():
        if (
            pass_id
            in engine.definitions
        ):
            engine.register(
                pass_id,
                handler,
                deterministic=True,
                opus_used=False,
            )


def semantic_pass_ids() -> tuple[
    str,
    ...,
]:
    return (
        "entity",
        "relationship",
        "topic",
        "contrast",
        "disambiguate",
        "cluster",
        "contradiction",
        "corroboration",
        "novelty",
        "relevance",
        "salience",
        "opus",
        "adjudicate",
        "summarize",
        "extract",
    )


def require_registered_passes(
    engine: pass_engine,
    pass_ids: Sequence[str],
) -> None:
    projection = engine.projection()

    registered = set(
        projection.get(
            "registered",
            [],
        )
    )

    missing = [
        pass_id
        for pass_id in pass_ids
        if pass_id not in registered
    ]

    if missing:
        semantic = [
            pass_id
            for pass_id in missing
            if pass_id
            in semantic_pass_ids()
        ]

        if semantic:
            raise engine_error(
                "semantic passes require "
                "their verified Opus binding "
                "before execution: "
                + ", ".join(
                    semantic
                )
            )

        raise engine_error(
            "unregistered passes: "
            + ", ".join(
                missing
            )
        )


def default_passes() -> tuple[
    str,
    ...,
]:
    return (
        "ingest",
        "normalize",
        "deduplicate",
        "identity",
        "provenance",
        "quality",
        "lineage",
        "category",
        "graph",
        "project",
    )


def parse_passes(
    value: str | None,
) -> tuple[str, ...]:
    if value is None:
        return default_passes()

    result = tuple(
        item.strip()
        for item in value.split(",")
        if item.strip()
    )

    if not result:
        raise engine_error(
            "at least one pass is required"
        )

    return result


def write_run(
    request: run_request,
    rows: list[
        dict[str, Any]
    ],
    receipts: Sequence[Any],
    profile: runtime_profile,
) -> dict[str, Any]:
    request.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    records_path = (
        request.output
        / "records.jsonl"
    )

    atomic_jsonl(
        records_path,
        rows,
    )

    category_paths: dict[
        str,
        str,
    ] = {}

    if any(
        "extr_partition" in row
        for row in rows
    ):
        for category_id in (
            profile.category_ids
        ):
            category_path = (
                request.output
                / "categories"
                / (
                    category_id
                    + ".jsonl"
                )
            )

            atomic_jsonl(
                category_path,
                (
                    row
                    for row in rows
                    if row.get(
                        "extr_partition",
                        {},
                    ).get(
                        "category"
                    )
                    == category_id
                ),
            )

            category_paths[
                category_id
            ] = str(
                category_path
            )

    datrix_path = (
        request.output
        / "datrix.jsonl"
    )

    datrix_rows = (
        row[
            "extr_datrix_projection"
        ]
        for row in rows
        if isinstance(
            row.get(
                "extr_datrix_projection"
            ),
            Mapping,
        )
    )

    datrix_count = atomic_jsonl(
        datrix_path,
        datrix_rows,
    )

    manifest = {
        "schema":
            "savant://runtime/extr/"
            "engine-run/1.0.0",
        "owner":
            owner,
        "authority_effect":
            authority_effect,
        "authoritative":
            False,
        "rebuildable":
            True,
        "request":
            request.projection(),
        "runtime_profile_digest":
            profile.source_digest,
        "record_count":
            len(rows),
        "records":
            str(records_path),
        "categories":
            category_paths,
        "datrix_projection":
            str(datrix_path),
        "datrix_projection_count":
            datrix_count,
        "datrix_storage_selected":
            False,
        "passes": [
            receipt.projection()
            for receipt in receipts
        ],
    }

    manifest[
        "run_digest"
    ] = digest(
        manifest
    )

    atomic_json(
        request.output
        / "manifest.json",
        manifest,
    )

    return manifest


def execute(
    request: run_request,
) -> dict[str, Any]:
    if not request.inputs:
        raise engine_error(
            "at least one input "
            "is required"
        )

    for path in request.inputs:
        if not path.is_file():
            raise engine_error(
                f"input unavailable: {path}"
            )

    if not request.categories.is_file():
        raise engine_error(
            "runtime category profile "
            f"unavailable: "
            f"{request.categories}"
        )

    if not request.pass_config.is_file():
        raise engine_error(
            "pass configuration "
            f"unavailable: "
            f"{request.pass_config}"
        )

    profile = (
        load_runtime_profile_file(
            request.categories
        )
    )

    definitions = (
        load_pass_definitions(
            request.pass_config
        )
    )

    engine = pass_engine(
        definitions
    )

    register_builtin_passes(
        engine
    )

    require_registered_passes(
        engine,
        request.passes,
    )

    imported = ingest_inputs(
        request.inputs
    )

    result = engine.execute(
        imported,
        request.passes,
        context={
            "runtime_profile":
                profile,
            "output":
                str(
                    request.output
                ),
        },
    )

    if not isinstance(
        result.value,
        list,
    ):
        raise engine_error(
            "pipeline must terminate "
            "with a record list"
        )

    rows = [
        dict(item)
        for item in result.value
        if isinstance(
            item,
            Mapping,
        )
    ]

    return write_run(
        request,
        rows,
        result.receipts,
        profile,
    )


def selftest() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="extr-engine-test-"
    ) as temporary:
        root = Path(
            temporary
        )

        input_path = (
            root
            / "input.json"
        )

        categories_path = (
            root
            / "categories.json"
        )

        passes_path = (
            root
            / "passes.json"
        )

        output_path = (
            root
            / "output"
        )

        input_path.write_text(
            json.dumps(
                [
                    {
                        "text":
                            "alpha_unique"
                    },
                    {
                        "text":
                            "beta_unique"
                    },
                    {
                        "text":
                            "unrelated"
                    },
                ]
            ),
            encoding="utf-8",
        )

        categories_path.write_text(
            json.dumps(
                {
                    "categories": [
                        {
                            "id":
                                "alpha",
                            "minimum_score":
                                1.0,
                            "signals": {
                                "identity": [
                                    "alpha_unique"
                                ]
                            },
                        },
                        {
                            "id":
                                "beta",
                            "minimum_score":
                                1.0,
                            "signals": {
                                "identity": [
                                    "beta_unique"
                                ]
                            },
                        },
                        {
                            "id":
                                "other"
                        },
                    ],
                    "catchall":
                        "other",
                }
            ),
            encoding="utf-8",
        )

        passes_path.write_text(
            json.dumps(
                {
                    "passes": [
                        {
                            "id":
                                pass_id,
                            "purpose":
                                pass_id,
                        }
                        for pass_id
                        in default_passes()
                    ]
                }
            ),
            encoding="utf-8",
        )

        request = run_request(
            inputs=(
                input_path,
            ),
            categories=
                categories_path,
            output=
                output_path,
            passes=
                default_passes(),
            pass_config=
                passes_path,
        )

        first = execute(
            request
        )

        first_records = (
            output_path
            / "records.jsonl"
        ).read_text(
            encoding="utf-8"
        )

        second = execute(
            request
        )

        second_records = (
            output_path
            / "records.jsonl"
        ).read_text(
            encoding="utf-8"
        )

        categories = []

        for line in (
            first_records.splitlines()
        ):
            row = json.loads(
                line
            )

            categories.append(
                row[
                    "extr_partition"
                ]["category"]
            )

        checks = {
            "three_records":
                first[
                    "record_count"
                ]
                == 3,
            "runtime_categories":
                categories
                == [
                    "alpha",
                    "beta",
                    "other",
                ],
            "deterministic_records":
                first_records
                == second_records,
            "deterministic_run":
                first[
                    "run_digest"
                ]
                == second[
                    "run_digest"
                ],
            "datrix_projection":
                first[
                    "datrix_projection_count"
                ]
                == 3,
            "no_datrix_storage":
                first[
                    "datrix_storage_selected"
                ]
                is False,
            "authority_none":
                first[
                    "authority_effect"
                ]
                == "none",
            "rebuildable":
                first[
                    "rebuildable"
                ]
                is True,
            "passes_chained":
                all(
                    first["passes"][
                        index
                    ][
                        "output_digest"
                    ]
                    == first["passes"][
                        index + 1
                    ][
                        "input_digest"
                    ]
                    for index
                    in range(
                        len(
                            first[
                                "passes"
                            ]
                        )
                        - 1
                    )
                ),
        }

        return {
            "schema":
                "savant://runtime/extr/"
                "engine-selftest/1.0.0",
            "ok":
                all(
                    checks.values()
                ),
            "checks":
                checks,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="extr-engine"
    )

    parser.add_argument(
        "inputs",
        nargs="*",
    )

    parser.add_argument(
        "--categories",
    )

    parser.add_argument(
        "--output",
    )

    parser.add_argument(
        "--passes",
    )

    parser.add_argument(
        "--pass-config",
        default=str(
            default_pass_config
        ),
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    args = parser.parse_args()

    if args.selftest:
        result = selftest()

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )

        return (
            0
            if result["ok"]
            else 1
        )

    if not args.inputs:
        raise engine_error(
            "at least one input "
            "path is required"
        )

    if not args.categories:
        raise engine_error(
            "--categories is required"
        )

    if not args.output:
        raise engine_error(
            "--output is required"
        )

    request = run_request(
        inputs=tuple(
            Path(path).resolve()
            for path
            in args.inputs
        ),
        categories=Path(
            args.categories
        ).resolve(),
        output=Path(
            args.output
        ).resolve(),
        passes=parse_passes(
            args.passes
        ),
        pass_config=Path(
            args.pass_config
        ).resolve(),
    )

    manifest = execute(
        request
    )

    print(
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
