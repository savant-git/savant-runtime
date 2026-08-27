#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


LEXICON_ROOT = Path(
    __file__
).resolve().parents[1]

RUNTIME_ROOT = (
    LEXICON_ROOT
    / "runtime"
)

BIN_ROOT = (
    LEXICON_ROOT
    / "bin"
)

DEFAULT_OUTPUT = (
    RUNTIME_ROOT
    / "compiled"
)

SUBSYSTEMS = {
    "lexicon": BIN_ROOT / "lexiconctl",
    "ontology": BIN_ROOT / "ontologyctl",
    "kindred": BIN_ROOT / "kindredctl",
    "instance": BIN_ROOT / "instancectl",
    "segue": BIN_ROOT / "seguectl",
    "projection": BIN_ROOT / "projectionctl",
    "constitution": BIN_ROOT / "constitutionctl",
}

EXECUTION_ORDER = [
    "lexicon",
    "ontology",
    "kindred",
    "instance",
    "segue",
    "projection",
    "constitution",
]


class RuntimeErrorBase(
    RuntimeError
):
    pass


class RuntimeEngine:

    def __init__(
        self,
    ) -> None:

        self.subsystems = dict(
            SUBSYSTEMS
        )

    def run_process(
        self,
        command: list[str],
    ) -> dict[str, Any]:

        completed = subprocess.run(
            command,
            cwd=str(
                LEXICON_ROOT
            ),
            capture_output=True,
            text=True,
            check=False,
        )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()

        parsed_stdout: Any = stdout

        if stdout:

            try:

                parsed_stdout = json.loads(
                    stdout
                )

            except json.JSONDecodeError:

                parsed_stdout = stdout

        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": parsed_stdout,
            "stderr": stderr,
            "passed": completed.returncode == 0,
        }

    def subsystem_command(
        self,
        subsystem: str,
        action: str,
        arguments: list[str] | None = None,
    ) -> list[str]:

        if subsystem not in self.subsystems:

            raise KeyError(
                subsystem
            )

        executable = self.subsystems[
            subsystem
        ]

        if not executable.exists():

            raise FileNotFoundError(
                str(
                    executable
                )
            )

        return [
            str(
                executable
            ),
            action,
            *(
                arguments
                or []
            ),
        ]

    def execute_subsystem(
        self,
        subsystem: str,
        action: str,
        arguments: list[str] | None = None,
    ) -> dict[str, Any]:

        command = self.subsystem_command(
            subsystem,
            action,
            arguments,
        )

        result = self.run_process(
            command
        )

        return {
            "subsystem": subsystem,
            "action": action,
            **result,
        }

    def validate(
        self,
        stop_on_failure: bool = False,
    ) -> dict[str, Any]:

        results = {}

        for subsystem in EXECUTION_ORDER:

            result = self.execute_subsystem(
                subsystem,
                "validate",
            )

            results[
                subsystem
            ] = result

            if (
                stop_on_failure
                and not result[
                    "passed"
                ]
            ):

                break

        failed = {
            name: result
            for name, result
            in results.items()
            if not result[
                "passed"
            ]
        }

        return {
            "operation": "validate",
            "passed": not failed,
            "subsystem_count": len(
                results
            ),
            "failed_count": len(
                failed
            ),
            "results": results,
        }

    def compile(
        self,
        output: Path,
        stop_on_failure: bool = True,
    ) -> dict[str, Any]:

        validation = self.validate(
            stop_on_failure=stop_on_failure
        )

        if not validation[
            "passed"
        ]:

            return {
                "operation": "compile",
                "passed": False,
                "phase": "validation",
                "validation": validation,
                "results": {},
            }

        output.mkdir(
            parents=True,
            exist_ok=True,
        )

        action_map = {
            "lexicon": (
                "compile",
                [],
            ),
            "ontology": (
                "compile",
                [],
            ),
            "kindred": (
                "compile",
                [],
            ),
            "instance": (
                "compile",
                [],
            ),
            "segue": (
                "compile",
                [],
            ),
            "projection": (
                "compile",
                [
                    "--output",
                    str(
                        output
                        / "projections"
                    ),
                ],
            ),
            "constitution": (
                "compile",
                [
                    "--output",
                    str(
                        output
                        / "constitution"
                    ),
                ],
            ),
        }

        results = {}

        for subsystem in EXECUTION_ORDER:

            action, arguments = action_map[
                subsystem
            ]

            result = self.execute_subsystem(
                subsystem,
                action,
                arguments,
            )

            results[
                subsystem
            ] = result

            if (
                stop_on_failure
                and not result[
                    "passed"
                ]
            ):

                break

        failed = {
            name: result
            for name, result
            in results.items()
            if not result[
                "passed"
            ]
        }

        manifest = self.build_manifest(
            output,
            validation,
            results,
        )

        self.write_json(
            output
            / "runtime_manifest.json",
            manifest,
        )

        return {
            "operation": "compile",
            "passed": not failed,
            "phase": (
                "complete"
                if not failed
                else "compile"
            ),
            "validation": validation,
            "results": results,
            "manifest": manifest,
        }

    def integrity(
        self,
        stop_on_failure: bool = False,
    ) -> dict[str, Any]:

        results = {}

        for subsystem in EXECUTION_ORDER:

            result = self.execute_subsystem(
                subsystem,
                "integrity",
            )

            results[
                subsystem
            ] = result

            if (
                stop_on_failure
                and not result[
                    "passed"
                ]
            ):

                break

        failed = {
            name: result
            for name, result
            in results.items()
            if not result[
                "passed"
            ]
        }

        return {
            "operation": "integrity",
            "passed": not failed,
            "subsystem_count": len(
                results
            ),
            "failed_count": len(
                failed
            ),
            "results": results,
        }

    def status(
        self,
    ) -> dict[str, Any]:

        records = {}

        for subsystem in EXECUTION_ORDER:

            executable = self.subsystems[
                subsystem
            ]

            records[
                subsystem
            ] = {
                "path": str(
                    executable
                ),
                "exists": executable.exists(),
                "executable": (
                    executable.exists()
                    and os.access(
                        executable,
                        os.X_OK,
                    )
                ),
            }

        ready = all(
            record[
                "exists"
            ]
            and record[
                "executable"
            ]
            for record in records.values()
        )

        return {
            "ready": ready,
            "lexicon_root": str(
                LEXICON_ROOT
            ),
            "runtime_root": str(
                RUNTIME_ROOT
            ),
            "subsystems": records,
            "execution_order": list(
                EXECUTION_ORDER
            ),
        }

    def collect_files(
        self,
        root: Path,
    ) -> list[dict[str, Any]]:

        files = []

        if not root.exists():

            return files

        for path in sorted(
            item
            for item in root.rglob(
                "*"
            )
            if item.is_file()
        ):

            digest = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()

            files.append(
                {
                    "path": str(
                        path.relative_to(
                            root
                        )
                    ),
                    "bytes": path.stat().st_size,
                    "sha256": digest,
                }
            )

        return files

    def build_manifest(
        self,
        output: Path,
        validation: dict[str, Any],
        compile_results: dict[str, Any],
    ) -> dict[str, Any]:

        files = self.collect_files(
            output
        )

        digest_payload = {
            "files": files,
            "execution_order": (
                EXECUTION_ORDER
            ),
        }

        digest = hashlib.sha256(
            json.dumps(
                digest_payload,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        return {
            "runtime": "savant-lexicon",
            "version": "1.0.0",
            "authority": (
                "lexicon:constitution"
            ),
            "output": str(
                output.resolve()
            ),
            "execution_order": list(
                EXECUTION_ORDER
            ),
            "validation_passed": (
                validation[
                    "passed"
                ]
            ),
            "compiled_subsystems": sorted(
                compile_results
            ),
            "files": files,
            "digest": digest,
            "dependencies": [
                str(
                    self.subsystems[
                        subsystem
                    ]
                )
                for subsystem
                in EXECUTION_ORDER
            ],
            "provenance": {
                "source": (
                    "runtime_engine.py"
                ),
                "confidence": (
                    "confirmed"
                ),
                "evidence": [
                    "lexiconctl",
                    "ontologyctl",
                    "kindredctl",
                    "instancectl",
                    "seguectl",
                    "projectionctl",
                    "constitutionctl",
                ],
            },
            "lineage": {
                "derived_from": [
                    (
                        "registry:"
                        "lexicon:core"
                    ),
                    (
                        "registry:"
                        "ontology:core"
                    ),
                    (
                        "registry:"
                        "kindred:core"
                    ),
                    (
                        "registry:"
                        "instance:core"
                    ),
                    (
                        "registry:"
                        "segue:core"
                    ),
                    (
                        "registry:"
                        "projection:core"
                    ),
                    (
                        "registry:"
                        "constitution:core"
                    ),
                ],
                "supersedes": [],
                "history": [
                    {
                        "version": "1.0.0",
                        "change": (
                            "Initial composed "
                            "runtime compilation"
                        ),
                    }
                ],
            },
        }

    def write_json(
        self,
        path: Path,
        payload: Any,
    ) -> None:

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = path.with_name(
            f".{path.name}.tmp"
        )

        temporary.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )

        os.replace(
            temporary,
            path,
        )

    def snapshot(
        self,
        output: Path,
    ) -> dict[str, Any]:

        status = self.status()
        validation = self.validate()
        integrity = self.integrity()

        compiled_files = self.collect_files(
            output
        )

        payload = {
            "status": status,
            "validation": validation,
            "integrity": integrity,
            "compiled_files": (
                compiled_files
            ),
        }

        digest = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
                default=str,
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        return {
            "passed": (
                status[
                    "ready"
                ]
                and validation[
                    "passed"
                ]
                and integrity[
                    "passed"
                ]
            ),
            "digest": digest,
            "status": status,
            "validation": validation,
            "integrity": integrity,
            "compiled_files": (
                compiled_files
            ),
        }


def main() -> int:

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "status"
    )

    validate_parser = subparsers.add_parser(
        "validate"
    )

    validate_parser.add_argument(
        "--stop-on-failure",
        action="store_true",
    )

    compile_parser = subparsers.add_parser(
        "compile"
    )

    compile_parser.add_argument(
        "--output",
        default=str(
            DEFAULT_OUTPUT
        ),
    )

    compile_parser.add_argument(
        "--continue-on-failure",
        action="store_true",
    )

    integrity_parser = subparsers.add_parser(
        "integrity"
    )

    integrity_parser.add_argument(
        "--stop-on-failure",
        action="store_true",
    )

    snapshot_parser = subparsers.add_parser(
        "snapshot"
    )

    snapshot_parser.add_argument(
        "--output",
        default=str(
            DEFAULT_OUTPUT
        ),
    )

    subsystem_parser = subparsers.add_parser(
        "subsystem"
    )

    subsystem_parser.add_argument(
        "subsystem",
        choices=EXECUTION_ORDER,
    )

    subsystem_parser.add_argument(
        "action"
    )

    subsystem_parser.add_argument(
        "arguments",
        nargs=argparse.REMAINDER,
    )

    args = parser.parse_args()

    engine = RuntimeEngine()

    if args.command == "status":

        result = engine.status()

    elif args.command == "validate":

        result = engine.validate(
            stop_on_failure=(
                args.stop_on_failure
            )
        )

    elif args.command == "compile":

        result = engine.compile(
            Path(
                args.output
            ),
            stop_on_failure=(
                not args.continue_on_failure
            ),
        )

    elif args.command == "integrity":

        result = engine.integrity(
            stop_on_failure=(
                args.stop_on_failure
            )
        )

    elif args.command == "snapshot":

        result = engine.snapshot(
            Path(
                args.output
            )
        )

    elif args.command == "subsystem":

        result = engine.execute_subsystem(
            args.subsystem,
            args.action,
            args.arguments,
        )

    else:

        raise RuntimeErrorBase(
            args.command
        )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    return (
        0
        if result.get(
            "passed",
            result.get(
                "ready",
                True,
            ),
        )
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
