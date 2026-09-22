#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from primitives import write_json


default_report_root = Path(
    "/root/savant-runtime/assurance/structure-intelligence"
)

default_output_root = Path(
    "/root/savant-runtime/evolution/structure-migration"
)

rubric_facilities = (
    "source",
    "contracts",
    "schemas",
    "adapters",
    "commands",
    "tests",
    "migrations",
    "tasks",
    "receipts",
)

cabal_laws = (
    "chorus",
    "commons",
    "covenant",
    "equinox",
    "gauntlet",
    "distillate",
    "severance",
    "cascade",
    "bridge",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"expected json object: {path}"
        )

    return value


def latest_report(root: Path) -> Path:
    candidates = [
        path
        for path in root.glob(
            "*/structure-intelligence.json"
        )
        if path.is_file()
        and path.stat().st_size > 0
    ]

    if not candidates:
        raise FileNotFoundError(
            "no structure-intelligence report found "
            f"beneath {root}"
        )

    return max(
        candidates,
        key=lambda path: path.stat().st_mtime_ns,
    )


def dependency_maps(
    edges: list[dict[str, Any]],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    dependencies: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    dependents: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for edge in edges:
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))

        if not source or not target:
            continue

        dependencies[source].append(edge)
        dependents[target].append(edge)

    return dependencies, dependents


def existing_rubric_facility(
    current: Path,
    rubric: str | None,
) -> str | None:
    if not rubric:
        return None

    rubric_path = Path(str(rubric))

    try:
        relative = current.relative_to(
            rubric_path
        )
    except ValueError:
        return None

    if not relative.parts:
        return None

    facility = relative.parts[0].lower()

    if facility not in rubric_facilities:
        return None

    return facility


def candidate_destination(
    record: dict[str, Any],
) -> tuple[str | None, str]:
    current = Path(
        str(record["relative_path"])
    )

    filename = current.name

    authority_state = str(
        record.get(
            "authority_state",
            "non-authority",
        )
    )

    projection_state = str(
        record.get(
            "projection_state",
            "non-projection",
        )
    )

    history_state = str(
        record.get(
            "history_state",
            "current-candidate",
        )
    )

    if authority_state != "non-authority":
        return (
            None,
            "authority-requires-resolution",
        )

    if projection_state != "non-projection":
        return (
            None,
            "projection-remains-in-place",
        )

    if history_state != "current-candidate":
        return (
            None,
            "history-remains-in-place",
        )

    rubric = record.get(
        "rubric_candidate"
    )

    cabal = record.get(
        "cabal_candidate"
    )

    rubric_confidence = float(
        record.get(
            "rubric_confidence",
            0.0,
        )
    )

    cabal_confidence = float(
        record.get(
            "cabal_confidence",
            0.0,
        )
    )

    artifact_kind = str(
        record.get(
            "artifact_kind",
            "other",
        )
    )

    if (
        rubric
        and rubric_confidence >= 0.80
    ):
        existing_facility = (
            existing_rubric_facility(
                current,
                str(rubric),
            )
        )

        if existing_facility:
            return (
                current.as_posix(),
                (
                    "existing-canonical-rubric-"
                    f"facility:{existing_facility}"
                ),
            )

    if (
        cabal
        and cabal_confidence >= 0.80
        and rubric_confidence < 0.80
    ):
        return (
            (
                Path(str(cabal))
                / "members"
                / filename
            ).as_posix(),
            "high-confidence-cabal",
        )

    if (
        rubric
        and rubric_confidence >= 0.80
    ):
        facility = {
            "source": "source",
            "schema": "schemas",
            "manifest": "schemas",
            "structured-record": "schemas",
            "service-unit": "commands",
            "environment": "contracts",
            "document": "contracts",
        }.get(artifact_kind)

        if facility is None:
            return (
                None,
                "unsupported-artifact-kind",
            )

        return (
            (
                Path(str(rubric))
                / facility
                / filename
            ).as_posix(),
            "high-confidence-rubric",
        )

    return (
        None,
        "classification-confidence-insufficient",
    )


def compile_artifacts(
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    records = report.get("files", [])
    edges = report.get(
        "dependencies",
        [],
    )

    if not isinstance(records, list):
        raise ValueError(
            "report.files must be a list"
        )

    if not isinstance(edges, list):
        raise ValueError(
            "report.dependencies must be a list"
        )

    dependencies, dependents = dependency_maps(
        edges
    )

    artifacts: list[dict[str, Any]] = []

    for record in records:
        if not isinstance(record, dict):
            continue

        current_path = str(
            record.get(
                "relative_path",
                "",
            )
        )

        if not current_path:
            continue

        destination, rationale = (
            candidate_destination(record)
        )

        blockers: list[str] = []
        retained_conditions: list[str] = []

        owner = record.get(
            "semantic_owner"
        )

        owner_confidence = float(
            record.get(
                "owner_confidence",
                0.0,
            )
        )

        if not owner:
            retained_conditions.append(
                "semantic-owner-unresolved"
            )

        if owner_confidence < 0.70:
            retained_conditions.append(
                "owner-confidence-below-threshold"
            )

        if record.get("parse_error"):
            blockers.append(
                "parse-error"
            )

        rubric_confidence = float(
            record.get(
                "rubric_confidence",
                0.0,
            )
        )

        cabal_confidence = float(
            record.get(
                "cabal_confidence",
                0.0,
            )
        )

        if (
            record.get("rubric_candidate")
            and record.get("cabal_candidate")
            and rubric_confidence >= 0.80
            and cabal_confidence >= 0.80
        ):
            blockers.append(
                "rubric-cabal-ambiguity"
            )

        if (
            destination is not None
            and destination != current_path
        ):
            blockers.extend(
                condition
                for condition
                in retained_conditions
                if condition not in blockers
            )

        artifacts.append(
            {
                "stable_id": (
                    "artifact:sha256:"
                    f"{record.get('sha256', '')}"
                ),
                "current_path": current_path,
                "canonical_path": destination,
                "artifact_kind": record.get(
                    "artifact_kind"
                ),
                "semantic_owner": owner,
                "owner_confidence": (
                    owner_confidence
                ),
                "rubric_owner": record.get(
                    "rubric_candidate"
                ),
                "rubric_confidence": (
                    rubric_confidence
                ),
                "shared_scope": record.get(
                    "cabal_candidate"
                ),
                "cabal_confidence": (
                    cabal_confidence
                ),
                "authority_state": record.get(
                    "authority_state"
                ),
                "projection_state": record.get(
                    "projection_state"
                ),
                "history_state": record.get(
                    "history_state"
                ),
                "source_sha256": record.get(
                    "sha256"
                ),
                "source_size": record.get(
                    "size"
                ),
                "dependencies": dependencies.get(
                    current_path,
                    [],
                ),
                "dependents": dependents.get(
                    current_path,
                    [],
                ),
                "compatibility_paths": [],
                "classification_rationale": (
                    rationale
                ),
                "blockers": blockers,
                "retained_conditions": (
                    retained_conditions
                ),
                "migration_action": "unresolved",
                "rollback_action": (
                    "restore-original-path"
                ),
                "validation_contract": [
                    "source-digest",
                    "destination-digest",
                    "syntax",
                    "dependency-resolution",
                    "reverse-dependency-resolution",
                    "compatibility",
                    "focused-verification",
                    "integration",
                    "receipt",
                ],
                "authorized": False,
                "mutation_performed": False,
            }
        )

    return artifacts


def apply_collisions(
    artifacts: list[dict[str, Any]],
) -> dict[str, list[str]]:
    destinations: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for artifact in artifacts:
        destination = artifact.get(
            "canonical_path"
        )

        if (
            destination
            and destination
            != artifact["current_path"]
        ):
            destinations[
                str(destination)
            ].append(
                str(
                    artifact["current_path"]
                )
            )

    collisions = {
        destination: sorted(paths)
        for destination, paths
        in destinations.items()
        if len(paths) > 1
    }

    for artifact in artifacts:
        destination = artifact.get(
            "canonical_path"
        )

        if destination in collisions:
            artifact["blockers"].append(
                "destination-collision"
            )

            artifact["collision_sources"] = (
                collisions[destination]
            )

        if artifact["blockers"]:
            artifact["migration_action"] = (
                "blocked"
            )

        elif destination is None:
            artifact["migration_action"] = (
                "remain"
            )

        elif (
            artifact["current_path"]
            == destination
        ):
            artifact["migration_action"] = (
                "retain"
            )

        else:
            artifact["migration_action"] = (
                "stage-move"
            )

    return collisions


def compile_manifest(
    report: dict[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    artifacts = compile_artifacts(report)
    collisions = apply_collisions(
        artifacts
    )

    counts = Counter(
        artifact["migration_action"]
        for artifact in artifacts
    )

    retained_condition_count = sum(
        len(
            artifact.get(
                "retained_conditions",
                [],
            )
        )
        for artifact in artifacts
    )

    return {
        "schema": (
            "savant://evolution/"
            "structure-migration-manifest/1.0.0"
        ),
        "generated_at": utc_now(),
        "source_report": {
            "path": str(report_path),
            "sha256": sha256_file(
                report_path
            ),
            "schema": report.get(
                "schema"
            ),
            "generated_at": report.get(
                "generated_at"
            ),
        },
        "authority": {
            "state": "proposal",
            "migration_authorized": False,
            "mutation_performed": False,
        },
        "canonical_constraints": {
            "rubric_facilities": list(
                rubric_facilities
            ),
            "cabal_laws": list(
                cabal_laws
            ),
            "existing_rubric_facility_action": (
                "retain"
            ),
            "unresolved_owner_action": (
                "remain-unmoved"
            ),
            "collision_action": "block",
            "destructive_move": "forbidden",
        },
        "summary": {
            "artifact_count": len(
                artifacts
            ),
            "stage_move_count": counts[
                "stage-move"
            ],
            "retain_count": counts[
                "retain"
            ],
            "remain_count": counts[
                "remain"
            ],
            "blocked_count": counts[
                "blocked"
            ],
            "collision_count": len(
                collisions
            ),
            "retained_condition_count": (
                retained_condition_count
            ),
        },
        "collisions": collisions,
        "artifacts": sorted(
            artifacts,
            key=lambda artifact: (
                artifact[
                    "migration_action"
                ],
                artifact[
                    "current_path"
                ],
            ),
        ),
    }


def write_summary(
    path: Path,
    manifest: dict[str, Any],
) -> None:
    summary = manifest["summary"]

    lines = [
        "# savant structure migration proposal",
        "",
        f"generated: {manifest['generated_at']}",
        "",
        "migration authorized: false",
        "mutation performed: false",
        "",
        "## summary",
        "",
    ]

    for key, value in summary.items():
        lines.append(
            f"- {key}: {value}"
        )

    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "compile a non-mutating savant "
            "structure migration manifest."
        )
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--report-root",
        type=Path,
        default=default_report_root,
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=default_output_root,
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        report_path = (
            arguments.report.resolve()
            if arguments.report
            else latest_report(
                arguments.report_root.resolve()
            )
        )

        if not report_path.is_file():
            raise FileNotFoundError(
                f"report unavailable: {report_path}"
            )

        report = load_json(
            report_path
        )

        manifest = compile_manifest(
            report,
            report_path,
        )

        run_id = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%dT%H%M%SZ"
        )

        output_directory = (
            arguments.output_root.resolve()
            / run_id
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=False,
        )

        manifest_path = (
            output_directory
            / "migration-manifest.json"
        )

        summary_path = (
            output_directory
            / "migration_proposal.md"
        )

        receipt_path = (
            output_directory
            / "receipt.json"
        )

        write_json(
            manifest_path,
            manifest,
        )

        write_summary(
            summary_path,
            manifest,
        )

        write_json(
            receipt_path,
            {
                "schema": (
                    "savant://receipt/"
                    "structure-migration-proposal/"
                    "1.0.0"
                ),
                "generated_at": utc_now(),
                "manifest": {
                    "path": str(
                        manifest_path
                    ),
                    "sha256": sha256_file(
                        manifest_path
                    ),
                },
                "summary": {
                    "path": str(
                        summary_path
                    ),
                    "sha256": sha256_file(
                        summary_path
                    ),
                },
                "source_report": (
                    manifest[
                        "source_report"
                    ]
                ),
                "result": manifest[
                    "summary"
                ],
                "migration_authorized": False,
                "mutation_performed": False,
            },
        )

    except Exception as exc:
        print(
            (
                f"error: "
                f"{type(exc).__name__}: {exc}"
            ),
            file=sys.stderr,
        )

        return 1

    print(
        f"manifest: {manifest_path}"
    )
    print(
        f"summary: {summary_path}"
    )
    print(
        f"receipt: {receipt_path}"
    )

    for key, value in manifest[
        "summary"
    ].items():
        print(
            f"{key}: {value}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
