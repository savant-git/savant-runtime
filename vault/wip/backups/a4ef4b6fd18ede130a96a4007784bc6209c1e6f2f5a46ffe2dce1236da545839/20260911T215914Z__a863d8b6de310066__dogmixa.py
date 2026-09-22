#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


OWNER = "exile:notary"
PRODIGAL = "prodigal:dogmixa"

SCHEMA = (
    "savant://runtime/notary/"
    "prodigal/dogmixa/1.0.0"
)


class DogmixaError(RuntimeError):
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
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def normalize_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).strip()


def normalize_terms(
    values: Sequence[Any],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                term
                for value in values
                if (
                    term
                    := normalize_text(
                        value
                    )
                )
            }
        )
    )


def require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise DogmixaError(
            f"{name} must be a mapping"
        )

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class ReconciliationFinding:
    code: str
    severity: str
    subject: str
    detail: str
    refs: tuple[str, ...]

    @property
    def finding_id(
        self,
    ) -> str:
        return (
            "dogmixa-finding:"
            + digest(
                {
                    "code": self.code,
                    "severity": (
                        self.severity
                    ),
                    "subject": (
                        self.subject
                    ),
                    "detail": (
                        self.detail
                    ),
                    "refs": list(
                        self.refs
                    ),
                }
            )[:32]
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        return {
            "finding_id": (
                self.finding_id
            ),
            "code": self.code,
            "severity": (
                self.severity
            ),
            "subject": (
                self.subject
            ),
            "detail": self.detail,
            "refs": list(
                self.refs
            ),
        }


def _finding(
    *,
    code: str,
    severity: str,
    subject: str,
    detail: str,
    refs: Sequence[Any] = (),
) -> ReconciliationFinding:
    return ReconciliationFinding(
        code=normalize_text(
            code
        ),
        severity=normalize_text(
            severity
        ),
        subject=normalize_text(
            subject
        ),
        detail=normalize_text(
            detail
        ),
        refs=normalize_terms(
            refs
        ),
    )


def inspect_pipeline(
    *,
    scrible_projection: Mapping[
        str,
        Any,
    ],
    earmarkd_projection: Mapping[
        str,
        Any,
    ],
    aledgerdly_projection: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    scrible = require_mapping(
        scrible_projection,
        "scrible_projection",
    )
    earmarkd = require_mapping(
        earmarkd_projection,
        "earmarkd_projection",
    )
    aledgerdly = require_mapping(
        aledgerdly_projection,
        "aledgerdly_projection",
    )

    if (
        normalize_text(
            scrible.get(
                "prodigal"
            )
        )
        != "prodigal:scrible"
    ):
        raise DogmixaError(
            "invalid Scrible projection"
        )

    if (
        normalize_text(
            earmarkd.get(
                "prodigal"
            )
        )
        != "prodigal:earmarkd"
    ):
        raise DogmixaError(
            "invalid Earmarkd projection"
        )

    if (
        normalize_text(
            aledgerdly.get(
                "prodigal"
            )
        )
        != "prodigal:aledgerdly"
    ):
        raise DogmixaError(
            "invalid Aledgerdly projection"
        )

    findings: list[
        ReconciliationFinding
    ] = []

    scrible_subject = normalize_text(
        scrible.get(
            "subject"
        )
    )
    earmarkd_subject = normalize_text(
        earmarkd.get(
            "subject"
        )
    )
    ledger_subject = normalize_text(
        aledgerdly.get(
            "subject"
        )
    )

    subjects = {
        value
        for value in (
            scrible_subject,
            earmarkd_subject,
            ledger_subject,
        )
        if value
    }

    if len(
        subjects
    ) != 1:
        findings.append(
            _finding(
                code=(
                    "subject-divergence"
                ),
                severity="conflict",
                subject=(
                    scrible_subject
                    or earmarkd_subject
                    or ledger_subject
                    or "unknown"
                ),
                detail=(
                    "pipeline projections do "
                    "not share one subject"
                ),
                refs=tuple(
                    subjects
                ),
            )
        )

    scrible_digest = normalize_text(
        scrible.get(
            "digest"
        )
    )

    earmarkd_source_digest = (
        normalize_text(
            earmarkd.get(
                "source_digest"
            )
        )
    )

    if (
        scrible_digest
        and earmarkd_source_digest
        and scrible_digest
        != earmarkd_source_digest
    ):
        findings.append(
            _finding(
                code=(
                    "scrible-earmarkd-"
                    "digest-divergence"
                ),
                severity="conflict",
                subject=(
                    earmarkd_subject
                    or scrible_subject
                    or "unknown"
                ),
                detail=(
                    "Earmarkd source digest "
                    "does not match Scrible "
                    "projection digest"
                ),
                refs=(
                    scrible_digest,
                    earmarkd_source_digest,
                ),
            )
        )

    earmarkd_digest = normalize_text(
        earmarkd.get(
            "digest"
        )
    )

    ledger_source_digest = (
        normalize_text(
            aledgerdly.get(
                "source_digest"
            )
        )
    )

    if (
        earmarkd_digest
        and ledger_source_digest
        and earmarkd_digest
        != ledger_source_digest
    ):
        findings.append(
            _finding(
                code=(
                    "earmarkd-ledger-"
                    "digest-divergence"
                ),
                severity="conflict",
                subject=(
                    ledger_subject
                    or earmarkd_subject
                    or "unknown"
                ),
                detail=(
                    "Aledgerdly source digest "
                    "does not match Earmarkd "
                    "projection digest"
                ),
                refs=(
                    earmarkd_digest,
                    ledger_source_digest,
                ),
            )
        )

    expected_earmark_ref = (
        normalize_text(
            earmarkd.get(
                "earmark_id"
            )
        )
    )

    ledger_source_ref = (
        normalize_text(
            aledgerdly.get(
                "source_ref"
            )
        )
    )

    if (
        expected_earmark_ref
        and ledger_source_ref
        and expected_earmark_ref
        != ledger_source_ref
    ):
        findings.append(
            _finding(
                code=(
                    "ledger-source-ref-"
                    "divergence"
                ),
                severity="conflict",
                subject=(
                    ledger_subject
                    or "unknown"
                ),
                detail=(
                    "Aledgerdly source "
                    "reference does not match "
                    "Earmarkd identity"
                ),
                refs=(
                    expected_earmark_ref,
                    ledger_source_ref,
                ),
            )
        )

    if (
        scrible.get(
            "complete"
        )
        is not True
    ):
        findings.append(
            _finding(
                code=(
                    "scrible-incomplete"
                ),
                severity="hold",
                subject=(
                    scrible_subject
                    or "unknown"
                ),
                detail=(
                    "Scrible material remains "
                    "incomplete"
                ),
                refs=(
                    normalize_text(
                        scrible.get(
                            "atom_id"
                        )
                    ),
                ),
            )
        )

    for label, projection in (
        ("scrible", scrible),
        ("earmarkd", earmarkd),
        (
            "aledgerdly",
            aledgerdly,
        ),
    ):
        if (
            projection.get(
                "authority_effect"
            )
            != "none"
        ):
            findings.append(
                _finding(
                    code=(
                        "unexpected-authority-"
                        "effect"
                    ),
                    severity="conflict",
                    subject=(
                        normalize_text(
                            projection.get(
                                "subject"
                            )
                        )
                        or "unknown"
                    ),
                    detail=(
                        f"{label} projection "
                        "claims an authority "
                        "effect"
                    ),
                    refs=(
                        normalize_text(
                            projection.get(
                                "digest"
                            )
                        ),
                    ),
                )
            )

    ordered_findings = tuple(
        sorted(
            findings,
            key=lambda finding: (
                finding.severity,
                finding.code,
                finding.subject,
                finding.finding_id,
            ),
        )
    )

    finding_projections = [
        finding.projection()
        for finding in ordered_findings
    ]

    conflict_count = sum(
        1
        for finding in ordered_findings
        if finding.severity
        == "conflict"
    )

    hold_count = sum(
        1
        for finding in ordered_findings
        if finding.severity
        == "hold"
    )

    payload = {
        "schema": SCHEMA,
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "subject": (
            scrible_subject
            or earmarkd_subject
            or ledger_subject
            or "unknown"
        ),
        "inputs": {
            "scrible": (
                scrible_digest
            ),
            "earmarkd": (
                earmarkd_digest
            ),
            "aledgerdly": (
                normalize_text(
                    aledgerdly.get(
                        "digest"
                    )
                )
            ),
        },
        "findings": (
            finding_projections
        ),
        "finding_count": len(
            finding_projections
        ),
        "conflict_count": (
            conflict_count
        ),
        "hold_count": hold_count,
        "consistent": (
            len(
                finding_projections
            )
            == 0
        ),
        "reconciliation_required": (
            len(
                finding_projections
            )
            > 0
        ),
        "reconciliation_performed": (
            False
        ),
        "canonical_output_generated": (
            False
        ),
        "verification_decision": None,
        "evidence_admitted": False,
        "attested": False,
        "canon_mutated": False,
        "ledger_mutated": False,
        "source_mutated": False,
        "automatic_reconciliation": False,
        "automatic_conflict_resolution": (
            False
        ),
        "authority_created": False,
        "authority_mutated": False,
        "authority_transferred": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
        "deterministic": True,
    }

    payload["digest"] = digest(
        payload
    )

    return payload


def status() -> dict[str, Any]:
    payload = {
        "schema": (
            "savant://runtime/notary/"
            "prodigal/dogmixa/"
            "status/1.0.0"
        ),
        "owner": OWNER,
        "prodigal": PRODIGAL,
        "purpose": (
            "inspect Notary Prodigal "
            "projections for deterministic "
            "cross-stage divergence without "
            "performing reconciliation"
        ),
        "capabilities": [
            "cross-stage-consistency-check",
            "subject-divergence-detection",
            "digest-lineage-check",
            "reference-lineage-check",
            "incomplete-input-hold",
            "authority-effect-detection",
            "conflict-preservation",
            "reconciliation-requirement-projection",
            "deterministic-findings",
        ],
        "verification_owner": OWNER,
        "can_verify": False,
        "can_admit_evidence": False,
        "can_attest": False,
        "can_reconcile": False,
        "can_resolve_conflicts": False,
        "can_generate_canonical_output": (
            False
        ),
        "can_mutate_canon": False,
        "can_mutate_ledger": False,
        "creates_authority": False,
        "mutates_authority": False,
        "persistent_store": False,
        "authoritative": False,
        "authority_effect": "none",
        "rebuildable": True,
    }

    payload["digest"] = digest(
        payload
    )

    return payload


def main() -> int:
    print(
        json.dumps(
            status(),
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
