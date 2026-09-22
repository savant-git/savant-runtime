#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from primitives import require_object
from primitives import bind_stable_id
from primitives import normalize_strings


runtime_root = Path("/root/savant-runtime")

underscore_root = (
    runtime_root
    / "ontology"
    / "obelisks"
    / "_template"
    / "segue"
    / "gates"
    / "_template"
    / "segue"
    / "innates"
    / "_template"
    / "segue"
    / "exiles"
    / "underscore"
)

schema_version = "savant.underscore.realization.adapter.v1"
authority_effect = "none"

default_timeout_seconds = 120
default_max_output_bytes = 262144


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


stable_id = bind_stable_id(digest)

def require_list(
    value: Any,
    name: str,
) -> list[Any]:
    if not isinstance(
        value,
        list,
    ):
        raise TypeError(
            f"{name} must be a list"
        )

    return value


@dataclass(frozen=True)
class AdapterReceipt:
    adapter: str
    adapter_version: str
    deterministic: bool
    duration_ms: int
    input_fingerprint: str
    output_fingerprint: str

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "adapter_version": (
                self.adapter_version
            ),
            "deterministic": (
                self.deterministic
            ),
            "duration_ms": (
                self.duration_ms
            ),
            "input_fingerprint": (
                self.input_fingerprint
            ),
            "output_fingerprint": (
                self.output_fingerprint
            ),
        }


class Realizer:
    adapter_name = "abstract"
    adapter_version = "1"
    deterministic = False

    def realize(
        self,
        assignment: dict[str, Any],
    ) -> tuple[
        dict[str, Any],
        AdapterReceipt,
    ]:
        started = time.monotonic_ns()

        input_fingerprint = digest(
            assignment
        )

        output = self._realize(
            assignment
        )

        require_object(
            output,
            "adapter output",
        )

        normalized = self._normalize_output(
            assignment,
            output,
        )

        elapsed_ms = int(
            (
                time.monotonic_ns()
                - started
            )
            / 1_000_000
        )

        receipt = AdapterReceipt(
            adapter=self.adapter_name,
            adapter_version=(
                self.adapter_version
            ),
            deterministic=(
                self.deterministic
            ),
            duration_ms=elapsed_ms,
            input_fingerprint=(
                input_fingerprint
            ),
            output_fingerprint=digest(
                normalized
            ),
        )

        return normalized, receipt

    def _realize(
        self,
        assignment: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def _normalize_output(
        assignment: dict[str, Any],
        output: dict[str, Any],
    ) -> dict[str, Any]:
        text = str(
            output.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            raise ValueError(
                "realizer returned empty text"
            )

        difference = str(
            output.get(
                "difference",
                "",
            )
        ).strip()

        assumptions = (
            normalize_strings(
                output.get(
                    "assumptions",
                    [],
                )
            )
        )

        constraint_notes = (
            normalize_strings(
                output.get(
                    "constraint_notes",
                    [],
                )
            )
        )

        return {
            "text": text,
            "difference": difference,
            "assumptions": assumptions,
            "constraint_notes": (
                constraint_notes
            ),
            "source_assignment_id": (
                str(
                    assignment.get(
                        "instance_id",
                        "",
                    )
                )
            ),
        }


class FixtureRealizer(
    Realizer
):
    adapter_name = "fixture"
    adapter_version = "1"
    deterministic = True

    def _realize(
        self,
        assignment: dict[str, Any],
    ) -> dict[str, Any]:
        lens = require_object(
            assignment.get(
                "lens",
                {},
            ),
            "assignment.lens",
        )

        subject = str(
            assignment.get(
                "subject",
                "",
            )
        ).strip()

        lens_id = str(
            lens.get(
                "id",
                "unknown",
            )
        ).strip()

        objective = str(
            lens.get(
                "objective",
                "",
            )
        ).strip()

        text = (
            f"{subject}. "
            f"Apply {lens_id}: "
            f"{objective}"
        ).strip()

        return {
            "text": text,
            "difference": (
                f"realized through "
                f"{lens_id}"
            ),
            "assumptions": [],
            "constraint_notes": [
                (
                    "fixture realization "
                    "does not establish "
                    "semantic quality"
                )
            ],
        }


class ExternalCommandRealizer(
    Realizer
):
    adapter_name = "external_command"
    adapter_version = "1"
    deterministic = False

    def __init__(
        self,
        command: list[str],
        *,
        timeout_seconds: int,
        max_output_bytes: int,
    ) -> None:
        if not command:
            raise ValueError(
                "external command is empty"
            )

        self.command = command

        self.timeout_seconds = max(
            int(timeout_seconds),
            1,
        )

        self.max_output_bytes = max(
            int(max_output_bytes),
            1024,
        )

    def _realize(
        self,
        assignment: dict[str, Any],
    ) -> dict[str, Any]:
        request = {
            "schema": (
                "savant.underscore."
                "realization.request.v1"
            ),
            "owner": "underscore",
            "authority_effect": "none",
            "assignment": assignment,
            "contract": {
                "response": {
                    "text": "string",
                    "difference": (
                        "string"
                    ),
                    "assumptions": "list",
                    "constraint_notes": (
                        "list"
                    ),
                },
                "requirements": [
                    (
                        "preserve supplied "
                        "hard constraints"
                    ),
                    (
                        "do not claim generated "
                        "content is authority"
                    ),
                    (
                        "return exactly one "
                        "candidate"
                    ),
                    (
                        "return one JSON object"
                    ),
                ],
            },
        }

        completed = subprocess.run(
            self.command,
            input=canonical_json(
                request
            ),
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
            env=os.environ.copy(),
        )

        stderr = (
            completed.stderr
            or ""
        )

        stdout = (
            completed.stdout
            or ""
        )

        if completed.returncode != 0:
            raise RuntimeError(
                "realization adapter "
                f"failed with exit "
                f"{completed.returncode}: "
                f"{stderr[:2000]}"
            )

        encoded = stdout.encode(
            "utf-8"
        )

        if len(encoded) > (
            self.max_output_bytes
        ):
            raise RuntimeError(
                "realization adapter "
                "output exceeded limit"
            )

        try:
            parsed = json.loads(
                stdout
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "realization adapter "
                "did not return valid JSON"
            ) from exc

        return require_object(
            parsed,
            "realization response",
        )


class RecordedRealizer(
    Realizer
):
    adapter_name = "recorded"
    adapter_version = "1"
    deterministic = True

    def __init__(
        self,
        records: dict[
            str,
            dict[str, Any],
        ],
    ) -> None:
        self.records = records

    def _realize(
        self,
        assignment: dict[str, Any],
    ) -> dict[str, Any]:
        assignment_id = str(
            assignment.get(
                "instance_id",
                "",
            )
        )

        if assignment_id not in (
            self.records
        ):
            raise KeyError(
                "no recorded realization "
                f"for {assignment_id}"
            )

        return self.records[
            assignment_id
        ]


class RealizationAdapter:
    def __init__(
        self,
        realizer: Realizer,
    ) -> None:
        self.realizer = realizer

    @staticmethod
    def _validate_assignment(
        assignment: Any,
        index: int,
    ) -> dict[str, Any]:
        assignment = require_object(
            assignment,
            f"assignment {index}",
        )

        instance_id = str(
            assignment.get(
                "instance_id",
                "",
            )
        ).strip()

        if not instance_id:
            raise ValueError(
                f"assignment {index} "
                "has no instance_id"
            )

        if str(
            assignment.get(
                "authority_effect",
                "none",
            )
        ) != "none":
            raise ValueError(
                f"assignment {index} "
                "attempts authority effect"
            )

        if str(
            assignment.get(
                "owner",
                "underscore",
            )
        ) != "underscore":
            raise ValueError(
                f"assignment {index} "
                "is not underscore-owned"
            )

        instruction = str(
            assignment.get(
                "instruction",
                "",
            )
        ).strip()

        if not instruction:
            raise ValueError(
                f"assignment {index} "
                "has no instruction"
            )

        return assignment

    @staticmethod
    def _realized_instance(
        assignment: dict[str, Any],
        realization: dict[str, Any],
        receipt: AdapterReceipt,
        index: int,
    ) -> dict[str, Any]:
        identity_basis = {
            "schema": schema_version,
            "source_assignment_id": (
                assignment[
                    "instance_id"
                ]
            ),
            "realization": realization,
            "adapter": (
                receipt.adapter
            ),
            "adapter_version": (
                receipt.adapter_version
            ),
            "index": index,
        }

        instance_id = stable_id(
            "instance",
            identity_basis,
        )

        lineage = []

        existing_lineage = (
            assignment.get(
                "lineage",
                [],
            )
        )

        if isinstance(
            existing_lineage,
            list,
        ):
            lineage.extend(
                normalize_strings(
                    existing_lineage
                )
            )

        lineage.append(
            str(
                assignment[
                    "instance_id"
                ]
            )
        )

        return {
            "instance_id": (
                instance_id
            ),
            "owner": "underscore",
            "kind": (
                "realized_divergent_candidate"
            ),
            "generation": int(
                assignment.get(
                    "generation",
                    0,
                )
            ),
            "text": (
                realization["text"]
            ),
            "difference": (
                realization[
                    "difference"
                ]
            ),
            "assumptions": (
                realization[
                    "assumptions"
                ]
            ),
            "constraint_notes": (
                realization[
                    "constraint_notes"
                ]
            ),
            "source": (
                "underscore.realization"
            ),
            "source_assignment_id": (
                assignment[
                    "instance_id"
                ]
            ),
            "lens": assignment.get(
                "lens",
                {},
            ),
            "subject": assignment.get(
                "subject",
                "",
            ),
            "lineage": lineage,
            "metadata": {
                "realization_adapter": (
                    receipt.adapter
                ),
                "adapter_version": (
                    receipt.adapter_version
                ),
                "adapter_deterministic": (
                    receipt.deterministic
                ),
                "input_fingerprint": (
                    receipt.input_fingerprint
                ),
                "output_fingerprint": (
                    receipt.output_fingerprint
                ),
            },
            "authority_effect": (
                authority_effect
            ),
        }

    @staticmethod
    def _segue(
        assignment: dict[str, Any],
        realized: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "source_assignment_id": (
                assignment[
                    "instance_id"
                ]
            ),
            "realized_instance_id": (
                realized[
                    "instance_id"
                ]
            ),
            "target": (
                "underscore.vessel"
            ),
        }

        return {
            "segue_id": stable_id(
                "segue",
                {
                    "type": (
                        "underscore."
                        "divergence."
                        "realization_to_vessel"
                    ),
                    "payload": payload,
                },
            ),
            "segue_type": (
                "underscore.divergence."
                "realization_to_vessel"
            ),
            "owner": "underscore",
            "source_instance_id": (
                realized[
                    "instance_id"
                ]
            ),
            "target": (
                "underscore.vessel"
            ),
            "authority_effect": (
                authority_effect
            ),
            "payload": payload,
        }

    def execute(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raw_assignments = (
            payload.get(
                "candidate_assignments",
                payload.get(
                    "assignments",
                    [],
                ),
            )
        )

        raw_assignments = (
            require_list(
                raw_assignments,
                "candidate_assignments",
            )
        )

        assignments = [
            self._validate_assignment(
                value,
                index,
            )
            for index, value
            in enumerate(
                raw_assignments
            )
        ]

        if not assignments:
            raise ValueError(
                "at least one candidate "
                "assignment is required"
            )

        realized_instances = []
        receipts = []
        segues = []
        failures = []

        for index, assignment in enumerate(
            assignments
        ):
            try:
                realization, receipt = (
                    self.realizer.realize(
                        assignment
                    )
                )

                realized = (
                    self._realized_instance(
                        assignment,
                        realization,
                        receipt,
                        index,
                    )
                )

                realized_instances.append(
                    realized
                )

                receipts.append(
                    {
                        "source_assignment_id": (
                            assignment[
                                "instance_id"
                            ]
                        ),
                        **receipt.as_dict(),
                    }
                )

                segues.append(
                    self._segue(
                        assignment,
                        realized,
                    )
                )

            except Exception as exc:
                failures.append(
                    {
                        "source_assignment_id": (
                            assignment.get(
                                "instance_id"
                            )
                        ),
                        "error_type": (
                            type(exc).__name__
                        ),
                        "error": str(
                            exc
                        )[:4000],
                    }
                )

        result = {
            "schema": schema_version,
            "owner": "underscore",
            "rubric": "vessel",
            "capability": (
                "candidate_realization"
            ),
            "authority_effect": (
                authority_effect
            ),
            "adapter": (
                self.realizer.adapter_name
            ),
            "adapter_version": (
                self.realizer.adapter_version
            ),
            "adapter_deterministic": (
                self.realizer.deterministic
            ),
            "input_count": len(
                assignments
            ),
            "realized_count": len(
                realized_instances
            ),
            "failure_count": len(
                failures
            ),
            "realized_instances": (
                realized_instances
            ),
            "segues": segues,
            "receipts": receipts,
            "failures": failures,
            "invariants": {
                "projection_only": True,
                "generated_content_is_not_authority": True,
                "assignments_preserved": True,
                "lineage_preserved": True,
                "provider_independent": True,
                "provider_failure_is_localized": True,
                "realizer_cannot_promote_canon": True,
                "realization_precedes_vessel_selection": True,
                "recorded_realization_replay_supported": True,
            },
        }

        result[
            "fingerprint"
        ] = digest(
            {
                "schema": (
                    schema_version
                ),
                "adapter": (
                    self.realizer.adapter_name
                ),
                "adapter_version": (
                    self.realizer.adapter_version
                ),
                "realized_instances": (
                    realized_instances
                ),
                "receipts": receipts,
                "failures": failures,
            }
        )

        return result


def load_json(
    path: str,
) -> Any:
    if path == "-":
        raw = sys.stdin.read()

    else:
        raw = Path(
            path
        ).read_text(
            encoding="utf-8"
        )

    return json.loads(
        raw
    )


def recorded_realizer(
    path: str,
) -> RecordedRealizer:
    data = load_json(
        path
    )

    if isinstance(
        data,
        list,
    ):
        records = {}

        for record in data:
            record = require_object(
                record,
                "record",
            )

            assignment_id = str(
                record.get(
                    "source_assignment_id",
                    "",
                )
            ).strip()

            if not assignment_id:
                raise ValueError(
                    "record missing "
                    "source_assignment_id"
                )

            records[
                assignment_id
            ] = record

    else:
        records = require_object(
            data,
            "record map",
        )

        records = {
            str(key): require_object(
                value,
                f"record {key}",
            )
            for key, value
            in records.items()
        }

    return RecordedRealizer(
        records
    )


def build_realizer(
    args: argparse.Namespace,
) -> Realizer:
    if args.adapter == "fixture":
        return FixtureRealizer()

    if args.adapter == "recorded":
        if not args.records:
            raise ValueError(
                "--records is required "
                "for recorded adapter"
            )

        return recorded_realizer(
            args.records
        )

    if args.adapter == (
        "external-command"
    ):
        command_text = (
            args.command
            or os.environ.get(
                "SAVANT_UNDERSCORE_REALIZER_COMMAND",
                "",
            )
        ).strip()

        if not command_text:
            raise ValueError(
                "external-command adapter "
                "requires --command or "
                "SAVANT_UNDERSCORE_REALIZER_COMMAND"
            )

        return ExternalCommandRealizer(
            shlex.split(
                command_text
            ),
            timeout_seconds=(
                args.timeout
            ),
            max_output_bytes=(
                args.max_output_bytes
            ),
        )

    raise ValueError(
        f"unsupported adapter: "
        f"{args.adapter}"
    )


def self_check() -> dict[str, Any]:
    assignments = []

    for index, lens in enumerate(
        (
            "assumption_inversion",
            "false_binary",
            "anti_twist",
        )
    ):
        assignments.append(
            {
                "instance_id": (
                    f"assignment_test_{index}"
                ),
                "owner": "underscore",
                "kind": (
                    "divergent_candidate_assignment"
                ),
                "generation": 0,
                "lens": {
                    "id": lens,
                    "objective": (
                        f"apply {lens}"
                    ),
                },
                "subject": (
                    "subvert an expected "
                    "ending"
                ),
                "instruction": (
                    "produce one concrete "
                    "divergent candidate"
                ),
                "authority_effect": "none",
            }
        )

    adapter = RealizationAdapter(
        FixtureRealizer()
    )

    first = adapter.execute(
        {
            "candidate_assignments": (
                assignments
            )
        }
    )

    second = adapter.execute(
        {
            "candidate_assignments": (
                assignments
            )
        }
    )

    if (
        first["realized_count"]
        != 3
    ):
        raise RuntimeError(
            "realization count failed"
        )

    if (
        first["failure_count"]
        != 0
    ):
        raise RuntimeError(
            "unexpected fixture "
            "realization failure"
        )

    if len(
        first["segues"]
    ) != 3:
        raise RuntimeError(
            "segue count failed"
        )

    if (
        first["fingerprint"]
        != second["fingerprint"]
    ):
        raise RuntimeError(
            "fixture determinism failed"
        )

    if any(
        item.get(
            "authority_effect"
        )
        != "none"
        for item
        in first[
            "realized_instances"
        ]
    ):
        raise RuntimeError(
            "authority invariant failed"
        )

    if any(
        item.get(
            "target"
        )
        != "underscore.vessel"
        for item
        in first[
            "segues"
        ]
    ):
        raise RuntimeError(
            "vessel routing failed"
        )

    return {
        "schema": (
            schema_version
        ),
        "authority_effect": (
            authority_effect
        ),
        "self_check": "passed",
        "adapter": "fixture",
        "realized_count": (
            first[
                "realized_count"
            ]
        ),
        "segue_count": len(
            first["segues"]
        ),
        "failure_count": (
            first[
                "failure_count"
            ]
        ),
        "fingerprint": (
            first[
                "fingerprint"
            ]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=(
            "underscore-realization-adapter"
        ),
        description=(
            "model-independent realization "
            "boundary for underscore "
            "divergent assignments"
        ),
    )

    parser.add_argument(
        "--adapter",
        choices=(
            "fixture",
            "recorded",
            "external-command",
        ),
        default="fixture",
    )

    parser.add_argument(
        "--records",
    )

    parser.add_argument(
        "--command",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=(
            default_timeout_seconds
        ),
    )

    parser.add_argument(
        "--max-output-bytes",
        type=int,
        default=(
            default_max_output_bytes
        ),
    )

    commands = (
        parser.add_subparsers(
            dest="action",
            required=True,
        )
    )

    execute = (
        commands.add_parser(
            "execute"
        )
    )

    execute.add_argument(
        "--input",
        required=True,
        help=(
            "compiler JSON path "
            "or - for stdin"
        ),
    )

    commands.add_parser(
        "self-check"
    )

    return parser


def main() -> int:
    args = (
        build_parser()
        .parse_args()
    )

    if args.action == (
        "self-check"
    ):
        result = (
            self_check()
        )

    elif args.action == (
        "execute"
    ):
        payload = load_json(
            args.input
        )

        payload = require_object(
            payload,
            "input",
        )

        realizer = (
            build_realizer(
                args
            )
        )

        adapter = (
            RealizationAdapter(
                realizer
            )
        )

        result = (
            adapter.execute(
                payload
            )
        )

    else:
        return 2

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
