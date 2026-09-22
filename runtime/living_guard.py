#!/usr/bin/env python3

from __future__ import annotations

import re

from pathlib import Path
from typing import Any


root = Path(
    "/root/savant-runtime"
).resolve()

canonical_relationship_term = "kindred"

historical_relationship_term = (
    "kin"
    + "ship"
)

high_confidence_secret_patterns = (
    (
        "openai_style_secret",
        re.compile(
            r"\bsk-[A-Za-z0-9_-]{20,}\b"
        ),
    ),
    (
        "github_token",
        re.compile(
            r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"
        ),
    ),
    (
        "google_api_key",
        re.compile(
            r"\bAIza[A-Za-z0-9_-]{25,}\b"
        ),
    ),
    (
        "private_key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
        ),
    ),
)


def check(
    check_id: str,
    passed: bool,
    *,
    message: str,
    severity: str = "error",
    evidence: Any = None,
) -> dict[str, Any]:
    result = {
        "check":
            check_id,

        "passed":
            bool(
                passed
            ),

        "severity":
            severity,

        "message":
            message,
    }

    if evidence is not None:
        result[
            "evidence"
        ] = evidence

    return result


def absolute_path(
    path: str,
) -> dict[str, Any]:
    candidate = Path(
        path
    )

    passed = candidate.is_absolute()

    return check(
        "absolute-path",
        passed,
        message=(
            "path is absolute"
            if passed
            else "mutation path is not absolute"
        ),
        evidence=str(
            candidate
        ),
    )


def runtime_containment(
    path: str,
) -> dict[str, Any]:
    candidate = Path(
        path
    ).resolve()

    try:
        candidate.relative_to(
            root
        )

        passed = (
            candidate
            != root
        )

    except ValueError:
        passed = False

    return check(
        "runtime-containment",
        passed,
        message=(
            "path is contained by the canonical savant runtime"
            if passed
            else "path escapes the canonical savant runtime"
        ),
        evidence=str(
            candidate
        ),
    )


def lowercase_savant_path(
    path: str,
) -> dict[str, Any]:
    candidate = Path(
        path
    ).resolve()

    try:
        relative = candidate.relative_to(
            root
        )

    except ValueError:
        return check(
            "lowercase-savant-path",
            True,
            severity="info",
            message=(
                "lowercase savant path rule is not applicable "
                "outside the canonical runtime"
            ),
            evidence=str(
                candidate
            ),
        )

    violations = [
        part
        for part
        in relative.parts
        if part
        != part.lower()
    ]

    passed = not violations

    return check(
        "lowercase-savant-path",
        passed,
        message=(
            "savant-owned path components are lowercase"
            if passed
            else "uppercase savant-owned path components detected"
        ),
        evidence={
            "path":
                str(
                    candidate
                ),

            "violations":
                violations,
        },
    )


def lowercase_identifier(
    identifier: str,
) -> dict[str, Any]:
    passed = (
        identifier
        == identifier.lower()
    )

    return check(
        "lowercase-identifier",
        passed,
        message=(
            "identifier is lowercase"
            if passed
            else "new savant-owned identifier is not lowercase"
        ),
        evidence=identifier,
    )


def canonical_terminology(
    text: str,
) -> dict[str, Any]:
    count = text.lower().count(
        historical_relationship_term
    )

    return check(
        "canonical-kindred-terminology",
        count == 0,
        severity=(
            "info"
            if count == 0
            else "warning"
        ),
        message=(
            "canonical relationship terminology preserved"
            if count == 0
            else (
                "historical relationship terminology detected; "
                "retain only when compatibility or history requires it"
            )
        ),
        evidence={
            "canonical":
                canonical_relationship_term,

            "historical_occurrences":
                count,
        },
    )


def secret_projection(
    text: str,
) -> dict[str, Any]:
    matches = []

    for name, pattern in (
        high_confidence_secret_patterns
    ):
        if pattern.search(
            text
        ):
            matches.append(
                name
            )

    passed = not matches

    return check(
        "secret-projection",
        passed,
        message=(
            "no high-confidence credential value detected"
            if passed
            else "high-confidence credential material detected"
        ),
        evidence={
            "matched_classes":
                matches
        },
    )


def duplicate_semantic_id(
    *,
    stream: str,
    identifier: str,
    existing_ids: set[str],
    allow_existing: bool,
) -> dict[str, Any]:
    exists = (
        identifier
        in existing_ids
    )

    passed = (
        allow_existing
        or not exists
    )

    return check(
        "duplicate-semantic-id",
        passed,
        message=(
            "semantic id is available"
            if not exists
            else (
                "existing semantic id accepted as evolution"
                if allow_existing
                else (
                    "semantic id already exists; "
                    "use evolution or supersession"
                )
            )
        ),
        evidence={
            "stream":
                stream,

            "id":
                identifier,

            "exists":
                exists,

            "allow_existing":
                allow_existing,
        },
    )


def evaluate_change(
    *,
    path: str | None = None,
    identifier: str | None = None,
    text: str | None = None,
    stream: str | None = None,
    existing_ids: set[str] | None = None,
    allow_existing: bool = False,
) -> dict[str, Any]:
    checks = []

    if path is not None:
        checks.extend(
            [
                absolute_path(
                    path
                ),
                runtime_containment(
                    path
                ),
                lowercase_savant_path(
                    path
                ),
            ]
        )

    if identifier is not None:
        checks.append(
            lowercase_identifier(
                identifier
            )
        )

    if text is not None:
        checks.extend(
            [
                canonical_terminology(
                    text
                ),
                secret_projection(
                    text
                ),
            ]
        )

    if (
        stream is not None
        and identifier is not None
        and existing_ids is not None
    ):
        checks.append(
            duplicate_semantic_id(
                stream=stream,
                identifier=identifier,
                existing_ids=existing_ids,
                allow_existing=allow_existing,
            )
        )

    failures = [
        item
        for item
        in checks
        if (
            not item[
                "passed"
            ]
            and item[
                "severity"
            ]
            == "error"
        )
    ]

    warnings = [
        item
        for item
        in checks
        if (
            not item[
                "passed"
            ]
            and item[
                "severity"
            ]
            == "warning"
        )
    ]

    return {
        "schema":
            "savant.living-guard.result.v2",

        "owner":
            "living-governance",

        "authority_effect":
            "guard",

        "allowed":
            not failures,

        "check_count":
            len(
                checks
            ),

        "failure_count":
            len(
                failures
            ),

        "warning_count":
            len(
                warnings
            ),

        "checks":
            checks,

        "credential_values_exposed":
            False,
    }


def status() -> dict[str, Any]:
    return {
        "schema":
            "savant.living-guard.status.v2",

        "owner":
            "living-governance",

        "authority_effect":
            "guard",

        "canonical_root":
            str(
                root
            ),

        "checks": [
            "absolute-path",
            "runtime-containment",
            "lowercase-savant-path",
            "lowercase-identifier",
            "canonical-kindred-terminology",
            "secret-projection",
            "duplicate-semantic-id",
        ],

        "hard_failures": [
            "absolute-path",
            "runtime-containment",
            "lowercase-savant-path",
            "lowercase-identifier",
            "secret-projection",
            "duplicate-semantic-id",
        ],

        "advisory_checks": [
            "canonical-kindred-terminology"
        ],

        "credential_values_exposed":
            False,

        "ready":
            True,
    }


__all__ = [
    "canonical_terminology",
    "duplicate_semantic_id",
    "evaluate_change",
    "lowercase_identifier",
    "lowercase_savant_path",
    "runtime_containment",
    "secret_projection",
    "status",
]
