#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).resolve()

EXILE_AUTHORITY_ROOT = (
    ROOT
    / "canon-system/authority/exiles"
)

OWNER_RESOLVER = (
    ROOT
    / "assurance/scanners/"
    "resolve_scyon_focal_owner.py"
)

DEFAULT_OUTPUT_ROOT = (
    ROOT
    / "runtime/reports/"
    "scyon-owner-proposals"
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


class ProposalError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ProposalError(message)


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def digest_value(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(value).encode(
            "utf-8"
        )
    ).hexdigest()


def atomic_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

        temporary = Path(
            handle.name
        )

    os.replace(
        temporary,
        path,
    )


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
        "cannot derive safe name",
    )

    return result


def parse_scalar(
    value: str,
) -> Any:
    value = value.strip()

    if not value:
        return ""

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {
            "'",
            '"',
        }
    ):
        return value[1:-1]

    if value.lower() == "true":
        return True

    if value.lower() == "false":
        return False

    if value.lower() in {
        "null",
        "none",
    }:
        return None

    try:
        if "." in value:
            return float(value)

        return int(value)

    except ValueError:
        return value


def parse_exile_authority(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"exile authority unavailable: {path}",
    )

    lines = path.read_text(
        encoding="utf-8",
        errors="strict",
    ).splitlines()

    result: dict[str, Any] = {
        "purpose": [],
    }

    section: str | None = None
    subsection: str | None = None

    for raw_line in lines:
        if not raw_line.strip():
            continue

        indent = (
            len(raw_line)
            - len(
                raw_line.lstrip(" ")
            )
        )

        text = raw_line.strip()

        if indent == 0:
            section = None
            subsection = None

            if ":" not in text:
                continue

            key, value = text.split(
                ":",
                1,
            )

            key = key.strip()

            if value.strip():
                result[key] = (
                    parse_scalar(value)
                )

            else:
                section = key

            continue

        if (
            indent == 2
            and section is not None
        ):
            if text.startswith("- "):
                continue

            if ":" not in text:
                continue

            key, value = text.split(
                ":",
                1,
            )

            key = key.strip()

            if value.strip():
                if section == "authority":
                    result[
                        f"authority.{key}"
                    ] = parse_scalar(
                        value
                    )

                elif section == "purpose":
                    result[
                        f"purpose.{key}"
                    ] = parse_scalar(
                        value
                    )

            else:
                subsection = key

            continue

        if (
            indent >= 2
            and text.startswith("- ")
            and section == "purpose"
            and subsection == "current"
        ):
            result[
                "purpose"
            ].append(
                text[2:].strip()
            )

    require(
        isinstance(
            result.get("id"),
            str,
        ),
        f"exile authority missing id: {path}",
    )

    return result


def exile_authority(
    owner_id: str,
) -> tuple[
    dict[str, Any],
    Path,
]:
    require(
        owner_id.startswith(
            "exile:"
        ),
        (
            "current proposal compiler "
            "supports exile owners only"
        ),
    )

    name = owner_id.split(
        ":",
        1,
    )[1]

    path = (
        EXILE_AUTHORITY_ROOT
        / f"{name}.yaml"
    ).resolve()

    record = parse_exile_authority(
        path
    )

    require(
        record.get("id")
        == owner_id,
        (
            "exile authority identity "
            f"mismatch: {path}"
        ),
    )

    return (
        record,
        path,
    )


def extract_service_assertion(
    implementation: Path,
    service_id: str,
) -> dict[str, Any]:
    require(
        implementation.is_file(),
        (
            "service implementation "
            f"unavailable: {implementation}"
        ),
    )

    tree = ast.parse(
        implementation.read_text(
            encoding="utf-8"
        ),
        filename=str(
            implementation
        ),
    )

    candidates: list[
        dict[str, Any]
    ] = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            ast.Dict,
        ):
            continue

        try:
            value = ast.literal_eval(
                node
            )

        except (
            ValueError,
            TypeError,
        ):
            continue

        if not isinstance(
            value,
            dict,
        ):
            continue

        if value.get("id") == service_id:
            candidates.append(
                value
            )

    require(
        len(candidates) == 1,
        (
            "expected exactly one literal "
            f"{service_id} service assertion "
            f"in {implementation}; "
            f"found {len(candidates)}"
        ),
    )

    return candidates[0]


def owner_resolution_receipt(
    service_id: str,
) -> dict[str, Any] | None:
    receipt = (
        ROOT
        / "runtime/reports/"
        "scyon-owner-resolution/"
        f"{safe_name(service_id)}.json"
    )

    if not receipt.is_file():
        return None

    try:
        value = json.loads(
            receipt.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError:
        return None

    if not isinstance(
        value,
        dict,
    ):
        return None

    return value


def validate_owner_authority(
    owner_id: str,
    *,
    permit_provisional: bool,
) -> dict[str, Any]:
    tier, name = (
        owner_id.split(
            ":",
            1,
        )
        if ":" in owner_id
        else (
            "",
            "",
        )
    )

    require(
        tier in SCYON_TIERS,
        (
            "proposed owner is not "
            "Scyon-bearing: "
            f"{owner_id}"
        ),
    )

    require(
        bool(name),
        "proposed owner name missing",
    )

    record, path = exile_authority(
        owner_id
    )

    status = str(
        record.get(
            "status",
            "",
        )
    )

    authority_state = str(
        record.get(
            "authority.state",
            "",
        )
    )

    if not permit_provisional:
        require(
            status == "accepted",
            (
                f"{owner_id} status is "
                f"{status!r}, not accepted"
            ),
        )

        require(
            authority_state
            == "accepted",
            (
                f"{owner_id} authority "
                f"state is "
                f"{authority_state!r}, "
                "not accepted"
            ),
        )

    return {
        "owner_id": owner_id,
        "owner_tier": tier,
        "authority_path": str(path),
        "authority_sha256": (
            sha256_file(path)
        ),
        "status": status,
        "authority_state": (
            authority_state
        ),
        "authority_confidence": (
            record.get(
                "authority.confidence"
            )
        ),
        "purpose": list(
            record.get(
                "purpose",
                [],
            )
        ),
        "eligible_under_current_policy": (
            status == "accepted"
            and authority_state
            == "accepted"
        ),
    }


def compile_proposal(
    *,
    service_id: str,
    implementation: Path,
    owner_id: str,
    permit_provisional: bool,
) -> dict[str, Any]:
    require(
        service_id.startswith(
            "service:"
        ),
        (
            "service identity must use "
            "service:<name>"
        ),
    )

    implementation = (
        implementation.resolve()
    )

    try:
        implementation.relative_to(
            ROOT
        )

    except ValueError as exc:
        raise ProposalError(
            (
                "implementation escapes "
                f"Savant root: {implementation}"
            )
        ) from exc

    service = extract_service_assertion(
        implementation,
        service_id,
    )

    owner = validate_owner_authority(
        owner_id,
        permit_provisional=(
            permit_provisional
        ),
    )

    previous_resolution = (
        owner_resolution_receipt(
            service_id
        )
    )

    relationship = {
        "type": (
            "implemented_through"
        ),
        "target": owner_id,
    }

    evidence = {
        "service_assertion": {
            "id": service.get("id"),
            "kind": service.get(
                "kind"
            ),
            "description": (
                service.get(
                    "description"
                )
            ),
            "dependencies": (
                service.get(
                    "dependencies",
                    [],
                )
            ),
            "relationships": (
                service.get(
                    "relationships",
                    [],
                )
            ),
            "metadata": (
                service.get(
                    "metadata",
                    {},
                )
            ),
            "implementation": str(
                implementation
            ),
            "implementation_sha256": (
                sha256_file(
                    implementation
                )
            ),
        },
        "proposed_owner": owner,
        "previous_owner_resolution": (
            previous_resolution
        ),
    }

    proposal: dict[
        str,
        Any,
    ] = {
        "schema": (
            "savant://authority/"
            "scyon-service-owner-proposal/"
            "1.0.0"
        ),
        "authority_state": (
            "proposed"
        ),
        "proposal_kind": (
            "constitutional-relationship"
        ),
        "target": service_id,
        "proposed_relationship": (
            relationship
        ),
        "proposed_scyon_owner_id": (
            owner_id
        ),
        "proposed_scyon_owner_tier": (
            owner[
                "owner_tier"
            ]
        ),
        "owner_authority": owner,
        "evidence": evidence,
        "inference": {
            "used": False,
            "semantic_similarity_used": (
                False
            ),
            "automatic_owner_selection": (
                False
            ),
        },
        "effects": {
            "authority_mutation_performed": (
                False
            ),
            "constitutional_assertion_mutated": (
                False
            ),
            "service_relationship_mutated": (
                False
            ),
            "focal_created": False,
            "focal_registered": False,
            "physical_mutation_performed": (
                False
            ),
        },
        "acceptance": {
            "accepted": False,
            "acceptance_required": True,
            "accepted_decision_id": None,
        },
    }

    proposal[
        "proposal_digest"
    ] = digest_value(
        proposal
    )

    return proposal


def self_test() -> dict[str, Any]:
    synthetic = {
        "target": (
            "service:test"
        ),
        "relationship": {
            "type": (
                "implemented_through"
            ),
            "target": (
                "exile:test"
            ),
        },
        "accepted": False,
    }

    first = digest_value(
        synthetic
    )

    second = digest_value(
        synthetic
    )

    require(
        first == second,
        (
            "canonical proposal digest "
            "is not deterministic"
        ),
    )

    return {
        "self_test": "passed",
        "deterministic": True,
        "automatic_owner_selection": False,
        "authority_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile a non-mutating proposal "
            "to bind a constitutional service "
            "to a Scyon-bearing implementation "
            "identity through implemented_through."
        )
    )

    parser.add_argument(
        "--service",
    )

    parser.add_argument(
        "--implementation",
        type=Path,
    )

    parser.add_argument(
        "--owner",
    )

    parser.add_argument(
        "--permit-provisional",
        action="store_true",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "command",
        choices=(
            "compile",
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
            "--service required",
        )

        require(
            arguments.implementation
            is not None,
            "--implementation required",
        )

        require(
            isinstance(
                arguments.owner,
                str,
            )
            and bool(
                arguments.owner
            ),
            "--owner required",
        )

        proposal = compile_proposal(
            service_id=(
                arguments.service
            ),
            implementation=(
                arguments.implementation
            ),
            owner_id=(
                arguments.owner
            ),
            permit_provisional=(
                arguments.permit_provisional
            ),
        )

        output = (
            arguments.output.resolve()
            if arguments.output
            is not None
            else (
                DEFAULT_OUTPUT_ROOT
                / (
                    safe_name(
                        arguments.service
                    )
                    + "--"
                    + safe_name(
                        arguments.owner
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
            raise ProposalError(
                (
                    "proposal output escapes "
                    f"Savant root: {output}"
                )
            ) from exc

        atomic_json(
            output,
            proposal,
        )

        print(
            json.dumps(
                {
                    "compiled": True,
                    "authority_state": (
                        "proposed"
                    ),
                    "service": (
                        arguments.service
                    ),
                    "proposed_owner": (
                        arguments.owner
                    ),
                    "owner_status": (
                        proposal[
                            "owner_authority"
                        ][
                            "status"
                        ]
                    ),
                    "owner_authority_state": (
                        proposal[
                            "owner_authority"
                        ][
                            "authority_state"
                        ]
                    ),
                    "accepted": False,
                    "authority_mutation_performed": False,
                    "focal_registered": False,
                    "output": str(
                        output
                    ),
                    "proposal_digest": (
                        proposal[
                            "proposal_digest"
                        ]
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    except (
        OSError,
        ValueError,
        SyntaxError,
        KeyError,
        ProposalError,
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
