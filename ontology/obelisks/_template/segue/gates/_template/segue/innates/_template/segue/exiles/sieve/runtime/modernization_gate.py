#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any, Mapping


schema = "savant://runtime/sieve/modernization-gate/2.0.1"
owner = "sieve"
authority_effect = "none"


required_requirements = (
    "historical_evidence_preserved",
    "historical_context_established",
    "current_authority_compared",
    "surviving_capability_identified",
    "current_savant_redesign_complete",
    "obsolete_assumptions_eliminated",
    "ownership_resolved",
    "integration_boundaries_resolved",
    "current_primitives_verified",
    "current_invariants_verified",
    "compatibility_verified",
    "implementation_authorized",
)


class modernization_gate_error(RuntimeError):
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
        ).encode("utf-8")
    ).hexdigest()


def normalize_requirements(
    value: Mapping[str, Any] | None,
) -> dict[str, bool]:
    source = (
        value
        if isinstance(value, Mapping)
        else {}
    )

    return {
        requirement: (
            source.get(requirement)
            is True
        )
        for requirement
        in required_requirements
    }


def evaluate(
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_identifier = (
        candidate.get("candidate_id")
    )

    requirements = (
        normalize_requirements(
            candidate.get(
                "modernization_requirements"
            )
            if isinstance(
                candidate.get(
                    "modernization_requirements"
                ),
                Mapping,
            )
            else None
        )
    )

    missing = [
        requirement
        for requirement, satisfied
        in requirements.items()
        if not satisfied
    ]

    candidate_present = bool(
        candidate_identifier
    )

    complete = (
        candidate_present
        and not missing
    )

    disposition = (
        "modernized-current-savant-candidate"
        if complete
        else "quarantine"
    )

    result = {
        "schema": schema,
        "owner": owner,
        "authority_effect": authority_effect,
        "authoritative": False,
        "candidate_id": (
            candidate_identifier
        ),
        "disposition": disposition,
        "gate_passed": complete,
        "implementation_eligible": (
            complete
        ),
        "requirements": requirements,
        "missing_requirements": missing,
        "boundaries": {
            "gate_creates_authority": False,
            "gate_changes_canon": False,
            "gate_modernizes_content": False,
            "gate_resolves_authority": False,
            "gate_authorizes_implementation": False,
            "historical_material_directly_implemented": False,
        },
    }

    result[
        "projection_digest"
    ] = digest(
        {
            "candidate_id": (
                candidate_identifier
            ),
            "disposition": (
                disposition
            ),
            "gate_passed": (
                complete
            ),
            "requirements": (
                requirements
            ),
            "missing_requirements": (
                missing
            ),
        }
    )

    return result


def selftest() -> dict[str, Any]:
    blank = evaluate(
        {
            "candidate_id": "blank",
        }
    )

    complete_requirements = {
        requirement: True
        for requirement
        in required_requirements
    }

    complete = evaluate(
        {
            "candidate_id": (
                "modernized"
            ),
            "modernization_requirements": (
                complete_requirements
            ),
        }
    )

    checks = {
        "authority_none": (
            authority_effect == "none"
        ),
        "owner_sieve": (
            owner == "sieve"
        ),
        "blank_blocked": (
            blank[
                "gate_passed"
            ]
            is False
        ),
        "blank_quarantined": (
            blank[
                "disposition"
            ]
            == "quarantine"
        ),
        "complete_classified": (
            complete[
                "disposition"
            ]
            == (
                "modernized-current-"
                "savant-candidate"
            )
        ),
        "complete_passes": (
            complete[
                "gate_passed"
            ]
            is True
        ),
        "gate_not_authority": (
            complete[
                "boundaries"
            ][
                "gate_creates_authority"
            ]
            is False
        ),
        "historical_direct_implementation_blocked": (
            complete[
                "boundaries"
            ][
                "historical_material_directly_implemented"
            ]
            is False
        ),
    }

    return {
        "schema": (
            "savant://runtime/sieve/"
            "modernization-gate-selftest/"
            "2.0.1"
        ),
        "ok": all(
            checks.values()
        ),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--selftest",
        action="store_true",
    )

    parser.add_argument(
        "--candidate-json",
    )

    arguments = parser.parse_args()

    if arguments.selftest:
        result = selftest()

    else:
        if not arguments.candidate_json:
            parser.error(
                "--candidate-json is required "
                "unless --selftest is used"
            )

        try:
            candidate = json.loads(
                arguments.candidate_json
            )
        except json.JSONDecodeError as exc:
            raise modernization_gate_error(
                "candidate json is invalid"
            ) from exc

        if not isinstance(
            candidate,
            Mapping,
        ):
            raise modernization_gate_error(
                "candidate json must be an object"
            )

        result = evaluate(
            candidate
        )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
