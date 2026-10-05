#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

LIVING_MODULE = (
    ROOT
    / "runtime/scyon/living_engine.py"
)

FOCAL_PATH = (
    ROOT
    / "runtime/scyon/focals/"
    "living-structure.json"
)

DEFAULT_DATABASE = (
    ROOT
    / "runtime/scyon/state/"
    "living-structure.sqlite3"
)


class StructureEngineError(
    RuntimeError
):
    pass


def load_living(
) -> Any:
    specification = (
        importlib.util.spec_from_file_location(
            "savant_living_engine",
            LIVING_MODULE,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise StructureEngineError(
            "living engine unavailable: "
            f"{LIVING_MODULE}"
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    sys.modules[
        specification.name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def sha256_file(
    path: Path,
) -> str:
    hasher = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            hasher.update(
                chunk
            )

    return hasher.hexdigest()


def latest_report(
    report_root: Path,
) -> Path:
    candidates = sorted(
        report_root.glob(
            "*/structure-intelligence.json"
        )
    )

    if not candidates:
        raise StructureEngineError(
            "no structure-intelligence "
            f"reports in {report_root}"
        )

    return candidates[
        -1
    ].resolve()


def report_summary(
    report: dict[str, Any],
) -> dict[str, Any]:
    summary = report.get(
        "summary"
    )

    if not isinstance(
        summary,
        dict,
    ):
        raise StructureEngineError(
            "structure report has "
            "no summary object"
        )

    keys = (
        "file_count",
        "source_count",
        "structured_record_count",
        "dependency_edge_count",
        "duplicate_group_count",
        "cross_owner_duplicate_group_count",
        "rubric_candidate_count",
        "cabal_candidate_count",
        "probable_multi_owner_cabal_count",
        "instance_candidate_count",
        "ownership_conflict_count",
        "migration_candidate_count",
        "parse_error_count",
        "unresolved_source_owner_count",
    )

    return {
        key: summary.get(
            key
        )
        for key in keys
    }


class LivingStructureEngine:
    def __init__(
        self,
        database: Path,
    ) -> None:
        self.living = (
            load_living()
        )

        self.focal = (
            self.living.LivingFocal.from_path(
                FOCAL_PATH
            )
        )

        self.engine = (
            self.living.LivingEngine(
                self.focal,
                database.resolve(),
                root=ROOT,
            )
        )

        self.engine.bootstrap()

        self.report_root = Path(
            self.focal.integrations[
                "report_root"
            ]
        )

        self.scanner = Path(
            self.focal.integrations[
                "scanner"
            ]
        )

        self.projection = Path(
            self.focal.integrations[
                "projection"
            ]
        )

    def close(
        self,
    ) -> None:
        self.engine.close()

    def run_scanner(
        self,
    ) -> Path:
        if not self.scanner.is_file():
            raise StructureEngineError(
                "scanner unavailable: "
                f"{self.scanner}"
            )

        existing = sorted(
            self.report_root.glob(
                "*/structure-intelligence.json"
            )
        )

        before = (
            existing[-1].resolve()
            if existing
            else None
        )

        completed = subprocess.run(
            [
                sys.executable,
                str(
                    self.scanner
                ),
            ],
            cwd=str(
                ROOT
            ),
            check=False,
            text=True,
            capture_output=True,
        )

        if (
            completed.returncode
            != 0
        ):
            message = (
                completed.stderr.strip()
                or completed.stdout.strip()
            )

            raise StructureEngineError(
                "scanner failed: "
                + message
            )

        after = latest_report(
            self.report_root
        )

        if (
            before is not None
            and after == before
        ):
            raise StructureEngineError(
                "scanner completed "
                "without producing "
                "a new report"
            )

        return after

    def ingest(
        self,
        report_path: Path,
    ) -> dict[str, Any]:
        report_path = (
            report_path.resolve()
        )

        report = json.loads(
            report_path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            report,
            dict,
        ):
            raise StructureEngineError(
                "report root must "
                "be an object"
            )

        if report.get(
            "mutation_performed"
        ) not in (
            False,
            None,
        ):
            raise StructureEngineError(
                "refusing report that "
                "records mutation"
            )

        if report.get(
            "migration_authorized"
        ) not in (
            False,
            None,
        ):
            raise StructureEngineError(
                "refusing report that "
                "records migration "
                "authorization"
            )

        summary = report_summary(
            report
        )

        observation = {
            "schema": report.get(
                "schema"
            ),
            "generated_at": report.get(
                "generated_at"
            ),
            "root": report.get(
                "root"
            ),
            "mutation_performed": (
                report.get(
                    "mutation_performed",
                    False,
                )
            ),
            "migration_authorized": (
                report.get(
                    "migration_authorized",
                    False,
                )
            ),
            "summary": summary,
        }

        observed = (
            self.engine.observe(
                "structure-intelligence",
                observation,
                source=str(
                    report_path
                ),
                source_digest=(
                    sha256_file(
                        report_path
                    )
                ),
                dependencies=[
                    str(
                        self.scanner
                    ),
                    (
                        "/root/savant-runtime/"
                        "canon/structure/"
                        "canonical_runtime_"
                        "structure.json"
                    ),
                ],
            )
        )

        projection = (
            self.project(
                summary,
                report_path,
                observed,
            )
        )

        return {
            "observation": (
                observed
            ),
            "projection": (
                projection
            ),
        }

    def project(
        self,
        summary: dict[str, Any],
        report_path: Path,
        observed: dict[str, Any],
    ) -> dict[str, Any]:
        checkpoint = (
            self.engine.checkpoint()
        )

        ownership_conflicts = (
            summary.get(
                "ownership_conflict_count"
            )
            or 0
        )

        unresolved_owners = (
            summary.get(
                "unresolved_source_owner_count"
            )
            or 0
        )

        if (
            ownership_conflicts > 0
            or unresolved_owners > 0
        ):
            next_action = (
                "reconcile ownership "
                "blockers before any "
                "migration"
            )

        else:
            next_action = (
                "compile non-mutating "
                "migration proposal "
                "from validated evidence"
            )

        payload = {
            "schema": (
                "savant://projection/"
                "living-structure/1.0.0"
            ),
            "authority_state": (
                "projection"
            ),
            "rebuildable": True,
            "engine_id": (
                self.focal.engine_id
            ),
            "scyon_id": (
                self.focal.scyon_id
            ),
            "source_report": {
                "path": str(
                    report_path
                ),
                "sha256": (
                    sha256_file(
                        report_path
                    )
                ),
            },
            "summary": (
                summary
            ),
            "observation": (
                observed
            ),
            "checkpoint": (
                checkpoint
            ),
            "migration_authorized": (
                False
            ),
            "mutation_performed": (
                False
            ),
            "next_action": (
                next_action
            ),
        }

        self.living.atomic_json(
            self.projection,
            payload,
        )

        return payload

    def cycle(
        self,
    ) -> dict[str, Any]:
        report_path = (
            self.run_scanner()
        )

        return self.ingest(
            report_path
        )

    def status(
        self,
    ) -> dict[str, Any]:
        status = (
            self.engine.status()
        )

        try:
            report = (
                latest_report(
                    self.report_root
                )
            )

            status[
                "latest_report"
            ] = {
                "path": str(
                    report
                ),
                "sha256": (
                    sha256_file(
                        report
                    )
                ),
            }

        except StructureEngineError:
            status[
                "latest_report"
            ] = None

        status[
            "projection"
        ] = str(
            self.projection
        )

        return status


def self_test(
    database: Path,
) -> dict[str, Any]:
    living = (
        load_living()
    )

    focal = (
        living.LivingFocal.from_path(
            FOCAL_PATH
        )
    )

    with living.LivingEngine(
        focal,
        database,
        root=ROOT,
    ) as engine:
        bootstrap = (
            engine.bootstrap()
        )

        first = engine.observe(
            "self-test",
            {
                "files": 10,
                "conflicts": 2,
            },
            source=(
                "synthetic:self-test"
            ),
            source_digest=(
                "a" * 64
            ),
        )

        duplicate = engine.observe(
            "self-test",
            {
                "files": 10,
                "conflicts": 2,
            },
            source=(
                "synthetic:self-test"
            ),
            source_digest=(
                "a" * 64
            ),
        )

        changed = engine.observe(
            "self-test",
            {
                "files": 11,
                "conflicts": 1,
            },
            source=(
                "synthetic:self-test"
            ),
            source_digest=(
                "b" * 64
            ),
        )

        validation = (
            engine.kernel.validate()
        )

        if (
            not first[
                "changed"
            ]
            or duplicate[
                "changed"
            ]
            or not changed[
                "changed"
            ]
            or not validation[
                "valid"
            ]
        ):
            raise StructureEngineError(
                "living structure "
                "self-test failed"
            )

        return {
            "self_test": (
                "passed"
            ),
            "bootstrap": (
                bootstrap
            ),
            "first_observation": (
                first
            ),
            "duplicate_suppressed": (
                not duplicate[
                    "changed"
                ]
            ),
            "drift_detected": (
                changed[
                    "changed"
                ]
            ),
            "validation": (
                validation
            ),
        }


def parser(
) -> argparse.ArgumentParser:
    command_parser = (
        argparse.ArgumentParser(
            description=(
                "Living Structure Engine: "
                "first Focal implementation "
                "of Scyon"
            )
        )
    )

    command_parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
    )

    command_parser.add_argument(
        "command",
        choices=(
            "cycle",
            "ingest-latest",
            "status",
            "self-test",
        ),
    )

    return command_parser


def main(
) -> int:
    arguments = (
        parser().parse_args()
    )

    database = (
        arguments.database.resolve()
    )

    if (
        arguments.command
        == "self-test"
    ):
        database.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if database.exists():
            database.unlink()

        result = self_test(
            database
        )

    else:
        engine = (
            LivingStructureEngine(
                database
            )
        )

        try:
            if (
                arguments.command
                == "cycle"
            ):
                result = (
                    engine.cycle()
                )

            elif (
                arguments.command
                == "ingest-latest"
            ):
                result = (
                    engine.ingest(
                        latest_report(
                            engine.report_root
                        )
                    )
                )

            else:
                result = (
                    engine.status()
                )

        finally:
            engine.close()

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        StructureEngineError,
    ) as exc:
        print(
            (
                "ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        raise SystemExit(1)
