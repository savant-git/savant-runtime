#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


DEFAULT_ROOT = Path("/root/savant-runtime")
DEFAULT_IDENTITY_ROOT = DEFAULT_ROOT / "edifices/identity"
DEFAULT_SCHEMA = (
    DEFAULT_ROOT
    / "tools/identity_quality/identity_quality.schema.json"
)
DEFAULT_REPORT_ROOT = (
    DEFAULT_ROOT
    / "reports/identity_quality"
)

KINDS = {
    "exile",
    "prodigal",
    "quirk",
}

FORBIDDEN_ACTIVE_TERMS = {
    "kindred": "kindred",
}

DISCOURAGED_UNIVERSAL_TERMS = {
    "entity",
    "universal_object",
    "universal_instance",
    "tessera",
    "ens",
    "hapax",
}

REQUIRED_TOP_LEVEL_FIELDS = (
    "id",
    "kind",
    "level",
    "version",
    "status",
    "identity",
    "purpose",
    "authority",
    "composition",
    "contracts",
    "capabilities",
    "dependencies",
    "relationships",
    "lineage",
    "provenance",
    "runtime",
    "security",
    "observability",
    "validation",
    "lifecycle",
    "apertures",
)

QUALITY_WEIGHTS = {
    "schema": 30,
    "authority": 10,
    "lineage": 8,
    "provenance": 8,
    "contracts": 8,
    "capabilities": 6,
    "dependencies": 5,
    "relationships": 5,
    "runtime": 6,
    "security": 5,
    "observability": 4,
    "validation": 3,
    "apertures": 2,
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str
    field: str | None = None
    value: Any = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }

        if self.field is not None:
            result["field"] = self.field

        if self.value is not None:
            result["value"] = self.value

        return result


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value)
    ).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def iter_definition_paths(
    root: Path,
) -> Iterable[Path]:
    yield from sorted(
        path
        for path in root.rglob(
            "definition.json"
        )
        if path.is_file()
    )


def json_path(
    error_path: Iterable[Any],
) -> str:
    parts = [
        str(part)
        for part in error_path
    ]

    return (
        "$"
        if not parts
        else "$." + ".".join(parts)
    )


def walk_strings(
    value: Any,
    path: str = "$",
) -> Iterable[tuple[str, str]]:
    if isinstance(
        value,
        dict,
    ):
        for key, child in value.items():
            child_path = (
                f"{path}.{key}"
            )

            yield from walk_strings(
                child,
                child_path,
            )

    elif isinstance(
        value,
        list,
    ):
        for index, child in enumerate(
            value
        ):
            child_path = (
                f"{path}[{index}]"
            )

            yield from walk_strings(
                child,
                child_path,
            )

    elif isinstance(
        value,
        str,
    ):
        yield path, value


def contains_data(
    value: Any,
) -> bool:
    if value is None:
        return False

    if isinstance(
        value,
        str,
    ):
        return bool(
            value.strip()
        )

    if isinstance(
        value,
        dict,
    ):
        return any(
            contains_data(child)
            for child in value.values()
        )

    if isinstance(
        value,
        list,
    ):
        return any(
            contains_data(child)
            for child in value
        )

    return True


def structure_score(
    document: dict[str, Any],
    schema_errors: int,
) -> dict[str, Any]:
    categories: dict[str, bool] = {}

    categories["schema"] = (
        schema_errors == 0
    )

    for category in (
        "authority",
        "lineage",
        "provenance",
        "contracts",
        "capabilities",
        "dependencies",
        "relationships",
        "runtime",
        "security",
        "observability",
        "validation",
        "apertures",
    ):
        categories[category] = (
            category in document
            and contains_data(
                document[category]
            )
        )

    score = sum(
        QUALITY_WEIGHTS[name]
        for name, passed
        in categories.items()
        if passed
    )

    maximum = sum(
        QUALITY_WEIGHTS.values()
    )

    percentage = round(
        score / maximum * 100,
        2,
    )

    if percentage >= 95:
        grade = "reference"
    elif percentage >= 85:
        grade = "robust"
    elif percentage >= 70:
        grade = "developing"
    elif percentage >= 40:
        grade = "structural"
    else:
        grade = "shell"

    return {
        "score": score,
        "maximum": maximum,
        "percentage": percentage,
        "grade": grade,
        "categories": categories,
    }


def audit_document(
    path: Path,
    identity_root: Path,
    validator: Draft202012Validator,
) -> dict[str, Any]:
    relative = path.relative_to(
        identity_root
    ).as_posix()

    findings: list[Finding] = []

    try:
        document = load_json(
            path
        )

    except Exception as exc:
        findings.append(
            Finding(
                severity="error",
                code="identity.json.invalid",
                path=relative,
                message=(
                    "Definition is not valid JSON."
                ),
                value=repr(exc),
            )
        )

        return {
            "path": relative,
            "valid": False,
            "identity_id": None,
            "kind": None,
            "findings": [
                finding.as_dict()
                for finding in findings
            ],
            "quality": {
                "score": 0,
                "maximum": sum(
                    QUALITY_WEIGHTS.values()
                ),
                "percentage": 0,
                "grade": "invalid",
                "categories": {},
            },
        }

    if not isinstance(
        document,
        dict,
    ):
        findings.append(
            Finding(
                severity="error",
                code="identity.root.invalid",
                path=relative,
                message=(
                    "Identity definition root "
                    "must be an object."
                ),
            )
        )

        return {
            "path": relative,
            "valid": False,
            "identity_id": None,
            "kind": None,
            "findings": [
                finding.as_dict()
                for finding in findings
            ],
            "quality": {
                "score": 0,
                "maximum": sum(
                    QUALITY_WEIGHTS.values()
                ),
                "percentage": 0,
                "grade": "invalid",
                "categories": {},
            },
        }

    schema_errors = sorted(
        validator.iter_errors(
            document
        ),
        key=lambda error: (
            list(error.absolute_path),
            error.message,
        ),
    )

    for error in schema_errors:
        findings.append(
            Finding(
                severity="error",
                code="identity.schema.invalid",
                path=relative,
                field=json_path(
                    error.absolute_path
                ),
                message=error.message,
            )
        )

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in document:
            findings.append(
                Finding(
                    severity="error",
                    code="identity.field.missing",
                    path=relative,
                    field=field,
                    message=(
                        "Required quality-contract "
                        "field is missing."
                    ),
                )
            )

    kind = document.get(
        "kind"
    )

    if kind not in KINDS:
        findings.append(
            Finding(
                severity="error",
                code="identity.kind.invalid",
                path=relative,
                field="kind",
                message=(
                    "Identity kind is not a "
                    "recognized exile, prodigal, "
                    "or quirk."
                ),
                value=kind,
            )
        )

    for field_path, value in walk_strings(
        document
    ):
        lower = value.lower()

        for forbidden, replacement in (
            FORBIDDEN_ACTIVE_TERMS.items()
        ):
            if forbidden in lower:
                findings.append(
                    Finding(
                        severity="error",
                        code=(
                            "terminology.forbidden"
                        ),
                        path=relative,
                        field=field_path,
                        message=(
                            f"Forbidden active term "
                            f"'{forbidden}' detected; "
                            f"use '{replacement}'."
                        ),
                        value=value,
                    )
                )

        for discouraged in (
            DISCOURAGED_UNIVERSAL_TERMS
        ):
            if discouraged in lower:
                findings.append(
                    Finding(
                        severity="warning",
                        code=(
                            "terminology.ambiguous"
                        ),
                        path=relative,
                        field=field_path,
                        message=(
                            "Ambiguous universal term "
                            "requires contextual review."
                        ),
                        value=value,
                    )
                )

    authority = document.get(
        "authority"
    )

    if (
        isinstance(authority, dict)
        and not authority.get("source")
    ):
        findings.append(
            Finding(
                severity="error",
                code="authority.source.missing",
                path=relative,
                field="authority.source",
                message=(
                    "Authority source is required."
                ),
            )
        )

    provenance = document.get(
        "provenance"
    )

    if isinstance(
        provenance,
        dict,
    ):
        source_hashes = provenance.get(
            "source_hashes"
        )

        if not isinstance(
            source_hashes,
            dict,
        ):
            findings.append(
                Finding(
                    severity="error",
                    code=(
                        "provenance.hashes.invalid"
                    ),
                    path=relative,
                    field=(
                        "provenance.source_hashes"
                    ),
                    message=(
                        "Provenance source hashes "
                        "must be an object."
                    ),
                )
            )

    runtime = document.get(
        "runtime"
    )

    if isinstance(
        runtime,
        dict,
    ):
        implementation = runtime.get(
            "implementation"
        )

        entrypoints = runtime.get(
            "entrypoints",
            [],
        )

        if (
            implementation == "complete"
            and not entrypoints
        ):
            findings.append(
                Finding(
                    severity="error",
                    code=(
                        "runtime.entrypoint.missing"
                    ),
                    path=relative,
                    field=(
                        "runtime.entrypoints"
                    ),
                    message=(
                        "Complete runtime "
                        "implementation requires "
                        "at least one entrypoint."
                    ),
                )
            )

    validation = document.get(
        "validation"
    )

    if isinstance(
        validation,
        dict,
    ):
        test_count = sum(
            len(
                validation.get(
                    field,
                    [],
                )
            )
            for field in (
                "unit_tests",
                "integration_tests",
                "property_tests",
                "security_tests",
            )
            if isinstance(
                validation.get(
                    field,
                    [],
                ),
                list,
            )
        )

        if (
            isinstance(runtime, dict)
            and runtime.get(
                "implementation"
            )
            in {
                "partial",
                "complete",
            }
            and test_count == 0
        ):
            findings.append(
                Finding(
                    severity="error",
                    code=(
                        "validation.tests.missing"
                    ),
                    path=relative,
                    field="validation",
                    message=(
                        "Implemented runtime requires "
                        "declared tests."
                    ),
                )
            )

    quality = structure_score(
        document,
        len(schema_errors),
    )

    error_count = sum(
        finding.severity == "error"
        for finding in findings
    )

    warning_count = sum(
        finding.severity == "warning"
        for finding in findings
    )

    return {
        "path": relative,
        "identity_id": document.get(
            "id"
        ),
        "kind": kind,
        "valid": error_count == 0,
        "error_count": error_count,
        "warning_count": warning_count,
        "quality": quality,
        "findings": [
            finding.as_dict()
            for finding in findings
        ],
        "source_sha256": hashlib.sha256(
            path.read_bytes()
        ).hexdigest(),
    }


def markdown_report(
    result: dict[str, Any],
) -> str:
    lines = [
        "# Savant Identity Quality Audit",
        "",
        f"- Generated: `{result['generated_at']}`",
        f"- Identity root: `{result['identity_root']}`",
        f"- Definitions: **{result['statistics']['definition_count']}**",
        f"- Valid: **{result['statistics']['valid_count']}**",
        f"- Invalid: **{result['statistics']['invalid_count']}**",
        f"- Errors: **{result['statistics']['error_count']}**",
        f"- Warnings: **{result['statistics']['warning_count']}**",
        f"- Audit digest: `{result['digest']}`",
        "",
        "## Quality distribution",
        "",
    ]

    for grade, count in sorted(
        result["statistics"][
            "quality_grades"
        ].items()
    ):
        lines.append(
            f"- `{grade}`: **{count}**"
        )

    lines.extend(
        [
            "",
            "## Definitions",
            "",
        ]
    )

    for record in result["records"]:
        quality = record["quality"]

        lines.append(
            "### "
            + (
                record.get("identity_id")
                or record["path"]
            )
        )

        lines.append("")
        lines.append(
            f"- Path: `{record['path']}`"
        )
        lines.append(
            f"- Kind: `{record.get('kind')}`"
        )
        lines.append(
            f"- Valid: **{record['valid']}**"
        )
        lines.append(
            f"- Grade: **{quality['grade']}**"
        )
        lines.append(
            f"- Score: **{quality['percentage']}%**"
        )
        lines.append("")

        findings = record.get(
            "findings",
            []
        )

        if not findings:
            lines.append(
                "No findings."
            )
            lines.append("")
            continue

        for finding in findings:
            field = finding.get(
                "field"
            )

            suffix = (
                f" at `{field}`"
                if field
                else ""
            )

            lines.append(
                f"- **{finding['severity'].upper()}** "
                f"`{finding['code']}`"
                f"{suffix}: "
                f"{finding['message']}"
            )

        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit Savant exile, prodigal, "
            "and quirk definitions against "
            "the identity quality contract."
        )
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
    )

    parser.add_argument(
        "--identity-root",
        type=Path,
        default=DEFAULT_IDENTITY_ROOT,
    )

    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
    )

    parser.add_argument(
        "--report-root",
        type=Path,
        default=DEFAULT_REPORT_ROOT,
    )

    parser.add_argument(
        "--strict",
        action="store_true",
    )

    args = parser.parse_args()

    root = args.root.resolve()
    identity_root = (
        args.identity_root.resolve()
    )
    schema_path = (
        args.schema.resolve()
    )
    report_root = (
        args.report_root.resolve()
    )

    if not root.is_dir():
        print(
            f"ERROR: Savant root missing: {root}",
            file=sys.stderr,
        )
        return 2

    if not identity_root.is_dir():
        print(
            "ERROR: identity root missing: "
            f"{identity_root}",
            file=sys.stderr,
        )
        return 2

    if not schema_path.is_file():
        print(
            f"ERROR: schema missing: {schema_path}",
            file=sys.stderr,
        )
        return 2

    try:
        schema = load_json(
            schema_path
        )
        Draft202012Validator.check_schema(
            schema
        )

    except (
        OSError,
        ValueError,
        SchemaError,
    ) as exc:
        print(
            f"ERROR: invalid schema: {exc}",
            file=sys.stderr,
        )
        return 2

    validator = Draft202012Validator(
        schema
    )

    records = [
        audit_document(
            path,
            identity_root,
            validator,
        )
        for path in iter_definition_paths(
            identity_root
        )
    ]

    statistics = {
        "definition_count": len(
            records
        ),
        "valid_count": sum(
            record["valid"]
            for record in records
        ),
        "invalid_count": sum(
            not record["valid"]
            for record in records
        ),
        "error_count": sum(
            record.get(
                "error_count",
                1,
            )
            for record in records
        ),
        "warning_count": sum(
            record.get(
                "warning_count",
                0,
            )
            for record in records
        ),
        "quality_grades": dict(
            sorted(
                Counter(
                    record["quality"]["grade"]
                    for record in records
                ).items()
            )
        ),
        "kinds": dict(
            sorted(
                Counter(
                    str(
                        record.get("kind")
                    )
                    for record in records
                ).items()
            )
        ),
    }

    result: dict[str, Any] = {
        "generated_at": utc_now(),
        "root": str(root),
        "identity_root": str(
            identity_root
        ),
        "schema": str(
            schema_path
        ),
        "statistics": statistics,
        "records": records,
    }

    result["digest"] = digest(
        result
    )

    report_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_json(
        report_root
        / "identity_quality_report.json",
        result,
    )

    write_json(
        report_root
        / "identity_quality_summary.json",
        {
            "generated_at": (
                result["generated_at"]
            ),
            "digest": result["digest"],
            "statistics": statistics,
        },
    )

    write_json(
        report_root
        / "identity_quality_failures.json",
        {
            "generated_at": (
                result["generated_at"]
            ),
            "digest": result["digest"],
            "records": [
                record
                for record in records
                if not record["valid"]
            ],
        },
    )

    (
        report_root
        / "identity_quality_report.md"
    ).write_text(
        markdown_report(
            result
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "passed": (
                    statistics[
                        "invalid_count"
                    ]
                    == 0
                ),
                "digest": result[
                    "digest"
                ],
                "reports": {
                    "full": str(
                        report_root
                        / (
                            "identity_quality_"
                            "report.json"
                        )
                    ),
                    "summary": str(
                        report_root
                        / (
                            "identity_quality_"
                            "summary.json"
                        )
                    ),
                    "failures": str(
                        report_root
                        / (
                            "identity_quality_"
                            "failures.json"
                        )
                    ),
                    "markdown": str(
                        report_root
                        / (
                            "identity_quality_"
                            "report.md"
                        )
                    ),
                },
                "statistics": statistics,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if (
        args.strict
        and statistics[
            "invalid_count"
        ]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
