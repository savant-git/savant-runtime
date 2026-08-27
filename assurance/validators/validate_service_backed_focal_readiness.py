#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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

OWNER_RESOLVER = (
    ROOT
    / "assurance/scanners/"
    "resolve_scyon_focal_owner.py"
)

REPORT_ROOT = (
    ROOT
    / "runtime/reports/"
    "scyon-focal-readiness"
)

SCYON_TIERS = {
    "trait",
    "quirk",
    "prodigal",
    "exile",
    "innate",
    "gate",
    "portal",
    "obelisk",
}


class ReadinessError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ReadinessError(message)


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON unavailable: {path}",
    )

    require(
        path.stat().st_size > 0,
        f"JSON empty: {path}",
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        raise ReadinessError(
            f"invalid JSON {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
    )

    return value


def safe_name(
    value: str,
) -> str:
    result = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "-",
        value,
    ).strip("-")

    require(
        bool(result),
        "cannot derive safe report name",
    )

    return result


def inside_root(
    raw: str,
    label: str,
) -> Path:
    path = Path(raw).resolve()

    try:
        path.relative_to(ROOT)

    except ValueError as exc:
        raise ReadinessError(
            f"{label} escapes Savant root: {path}"
        ) from exc

    return path


def resolve_owner(
    service_id: str,
) -> tuple[
    dict[str, Any],
    Path,
]:
    require(
        OWNER_RESOLVER.is_file(),
        (
            "owner resolver unavailable: "
            f"{OWNER_RESOLVER}"
        ),
    )

    receipt = (
        ROOT
        / "runtime/reports/"
        "scyon-owner-resolution/"
        f"{safe_name(service_id)}.json"
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(OWNER_RESOLVER),
            service_id,
            "--output",
            str(receipt),
        ],
        cwd=str(ROOT),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    require(
        completed.returncode
        in (0, 2),
        (
            "owner resolver failed:\n"
            f"{completed.stdout}"
        ),
    )

    return (
        load_json(receipt),
        receipt,
    )


def validate_receipt(
    service_id: str,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    schema = receipt.get(
        "schema"
    )

    require(
        isinstance(schema, str)
        and schema.startswith(
            "savant://assurance/"
            "scyon-owner-resolution/"
        ),
        (
            "unsupported owner-resolution "
            f"schema: {schema!r}"
        ),
    )

    require(
        receipt.get("target")
        == service_id,
        "owner receipt target mismatch",
    )

    require(
        receipt.get(
            "inference_used"
        )
        is False,
        (
            "owner resolution must not "
            "use inference"
        ),
    )

    require(
        receipt.get(
            "semantic_similarity_used"
        )
        is False,
        (
            "owner resolution must not "
            "use semantic similarity"
        ),
    )

    require(
        receipt.get(
            "authority_mutation_performed"
        )
        is False,
        (
            "owner resolution must not "
            "mutate authority"
        ),
    )

    require(
        receipt.get(
            "physical_mutation_performed"
        )
        is False,
        (
            "owner resolution must not "
            "perform physical mutation"
        ),
    )

    resolution = receipt.get(
        "resolution"
    )

    owner_id = receipt.get(
        "scyon_owner_id"
    )

    owner_tier = receipt.get(
        "scyon_owner_tier"
    )

    if (
        resolution
        == "explicit-owner-found"
    ):
        require(
            isinstance(owner_id, str)
            and ":" in owner_id,
            (
                "resolved owner_id "
                "is invalid"
            ),
        )

        require(
            owner_tier
            in SCYON_TIERS,
            (
                "resolved owner_tier "
                "is not Scyon-bearing"
            ),
        )

        require(
            owner_id.split(
                ":",
                1,
            )[0]
            == owner_tier,
            (
                "resolved owner_id and "
                "owner_tier disagree"
            ),
        )

    else:
        require(
            owner_id is None,
            (
                "non-resolved receipt "
                "must not claim owner_id"
            ),
        )

        require(
            owner_tier is None,
            (
                "non-resolved receipt "
                "must not claim owner_tier"
            ),
        )

    return {
        "resolution": resolution,
        "owner_id": owner_id,
        "owner_tier": owner_tier,
    }


def implementation_status(
    implementation: Path,
) -> dict[str, Any]:
    return {
        "path": str(
            implementation
        ),
        "exists": (
            implementation.is_file()
        ),
        "sha256": (
            sha256_file(
                implementation
            )
            if implementation.is_file()
            else None
        ),
    }


def evaluate(
    *,
    service_id: str,
    focal_kind: str,
    implementation: Path,
) -> dict[str, Any]:
    require(
        service_id.startswith(
            "service:"
        ),
        (
            "service_id must use "
            "service:<identity>"
        ),
    )

    require(
        bool(
            focal_kind.strip()
        ),
        "focal_kind cannot be empty",
    )

    implementation = (
        implementation.resolve()
    )

    try:
        implementation.relative_to(
            ROOT
        )

    except ValueError as exc:
        raise ReadinessError(
            (
                "implementation escapes "
                f"Savant root: {implementation}"
            )
        ) from exc

    (
        receipt,
        receipt_path,
    ) = resolve_owner(
        service_id
    )

    owner = validate_receipt(
        service_id,
        receipt,
    )

    implementation_state = (
        implementation_status(
            implementation
        )
    )

    blockers: list[
        dict[str, str]
    ] = []

    if not implementation_state[
        "exists"
    ]:
        blockers.append(
            {
                "code": (
                    "implementation-missing"
                ),
                "message": (
                    "Verified implementation "
                    "file is unavailable."
                ),
            }
        )

    resolution = owner[
        "resolution"
    ]

    if resolution == "unresolved":
        blockers.append(
            {
                "code": (
                    "implementation-owner-unresolved"
                ),
                "message": (
                    "No explicit "
                    "implemented_through "
                    "Scyon-bearing identity "
                    "was found."
                ),
            }
        )

    elif (
        resolution
        == "authority-conflict"
    ):
        blockers.append(
            {
                "code": (
                    "implementation-owner-conflict"
                ),
                "message": (
                    "Conflicting highest-authority "
                    "implementation-owner evidence "
                    "exists."
                ),
            }
        )

    elif (
        resolution
        != "explicit-owner-found"
    ):
        blockers.append(
            {
                "code": (
                    "unsupported-owner-resolution"
                ),
                "message": (
                    "Owner resolver returned "
                    f"unsupported state: {resolution}"
                ),
            }
        )

    ready = (
        not blockers
        and owner[
            "owner_id"
        ]
        is not None
        and owner[
            "owner_tier"
        ]
        is not None
        and implementation_state[
            "exists"
        ]
    )

    return {
        "schema": (
            "savant://assurance/"
            "service-backed-focal-readiness/"
            "1.0.0"
        ),
        "authority_state": (
            "projection"
        ),
        "service_id": service_id,
        "proposed_focal_kind": (
            focal_kind
        ),
        "implementation": (
            implementation_state
        ),
        "owner_resolution": {
            "resolution": (
                owner[
                    "resolution"
                ]
            ),
            "owner_id": (
                owner[
                    "owner_id"
                ]
            ),
            "owner_tier": (
                owner[
                    "owner_tier"
                ]
            ),
            "receipt": str(
                receipt_path
            ),
            "receipt_sha256": (
                sha256_file(
                    receipt_path
                )
            ),
        },
        "ready_for_focal_definition": (
            ready
        ),
        "ready_for_registry": False,
        "registry_registration_performed": False,
        "authority_mutation_performed": False,
        "physical_mutation_performed": False,
        "focal_creation_performed": False,
        "blockers": blockers,
        "next_legal_action": (
            "Create and validate the service-backed "
            "Focal definition using the resolved "
            "owner receipt."
            if ready
            else (
                "Establish or reconcile explicit "
                "implemented_through authority "
                "before creating the Focal."
            )
        ),
    }


def write_report(
    report: dict[str, Any],
    output: Path,
) -> None:
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = (
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    temporary = (
        output.with_suffix(
            output.suffix
            + ".tmp"
        )
    )

    temporary.write_text(
        payload,
        encoding="utf-8",
    )

    os.replace(
        temporary,
        output,
    )


def self_test() -> dict[str, Any]:
    unresolved = {
        "schema": (
            "savant://assurance/"
            "service-backed-focal-readiness/"
            "1.0.0"
        ),
        "ready_for_focal_definition": False,
        "blockers": [
            {
                "code": (
                    "implementation-owner-unresolved"
                )
            }
        ],
    }

    require(
        unresolved[
            "ready_for_focal_definition"
        ]
        is False,
        "self-test readiness boundary failed",
    )

    require(
        unresolved[
            "blockers"
        ][0][
            "code"
        ]
        == (
            "implementation-owner-unresolved"
        ),
        "self-test blocker failed",
    )

    return {
        "self_test": "passed",
        "fail_closed": True,
        "authority_mutation_performed": False,
        "physical_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate readiness for a "
            "service-backed Scyon Focal "
            "without creating it."
        )
    )

    parser.add_argument(
        "--service",
        default=None,
    )

    parser.add_argument(
        "--focal-kind",
        default=None,
    )

    parser.add_argument(
        "--implementation",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "command",
        choices=(
            "check",
            "self-test",
        ),
    )

    arguments = (
        parser.parse_args()
    )

    try:
        if (
            arguments.command
            == "self-test"
        ):
            print(
                json.dumps(
                    self_test(),
                    indent=2,
                    sort_keys=True,
                )
            )

            return 0

        require(
            isinstance(
                arguments.service,
                str,
            )
            and bool(
                arguments.service
            ),
            (
                "--service required "
                "for check"
            ),
        )

        require(
            isinstance(
                arguments.focal_kind,
                str,
            )
            and bool(
                arguments.focal_kind
            ),
            (
                "--focal-kind required "
                "for check"
            ),
        )

        require(
            arguments.implementation
            is not None,
            (
                "--implementation required "
                "for check"
            ),
        )

        report = evaluate(
            service_id=(
                arguments.service
            ),
            focal_kind=(
                arguments.focal_kind
            ),
            implementation=(
                arguments.implementation
            ),
        )

        output = (
            arguments.output.resolve()
            if arguments.output
            is not None
            else (
                REPORT_ROOT
                / (
                    safe_name(
                        arguments.service
                    )
                    + ".json"
                )
            )
        )

        try:
            output.relative_to(
                ROOT
            )

        except ValueError as exc:
            raise ReadinessError(
                (
                    "output escapes "
                    f"Savant root: {output}"
                )
            ) from exc

        write_report(
            report,
            output,
        )

        summary = {
            "service_id": (
                report[
                    "service_id"
                ]
            ),
            "ready_for_focal_definition": (
                report[
                    "ready_for_focal_definition"
                ]
            ),
            "resolution": (
                report[
                    "owner_resolution"
                ][
                    "resolution"
                ]
            ),
            "owner_id": (
                report[
                    "owner_resolution"
                ][
                    "owner_id"
                ]
            ),
            "blocker_count": len(
                report[
                    "blockers"
                ]
            ),
            "output": str(
                output
            ),
        }

        print(
            json.dumps(
                summary,
                indent=2,
                sort_keys=True,
            )
        )

        return (
            0
            if report[
                "ready_for_focal_definition"
            ]
            else 3
        )

    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        ReadinessError,
    ) as exc:
        print(
            (
                "ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
