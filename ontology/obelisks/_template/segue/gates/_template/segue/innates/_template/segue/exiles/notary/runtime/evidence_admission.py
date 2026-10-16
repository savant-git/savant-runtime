#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


OWNER = "exile:notary"
MECHANICS_OWNER = "living:thryce"

SCHEMA = (
    "savant://runtime/notary/"
    "evidence-admission/1.0.0"
)


class EvidenceAdmissionError(
    RuntimeError
):
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
    return str(
        value
        or ""
    ).strip()


def normalize_terms(
    values: Sequence[Any],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                normalized
                for value in values
                if (
                    normalized
                    := normalize_text(
                        value
                    )
                )
            }
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class EvidenceAdmissionDecision:
    subject: str
    candidate_digest: str
    assurance_digest: str
    decision: str
    reason: str
    evidence_ids: tuple[str, ...]
    provenance: Any
    lineage: Any
    dependencies: tuple[str, ...]

    @property
    def admitted(
        self,
    ) -> bool:
        return (
            self.decision
            == "admit"
        )

    @property
    def verified(
        self,
    ) -> bool:
        return (
            self.decision
            == "admit"
        )

    @property
    def evidence_id(
        self,
    ) -> str:
        material = {
            "subject": (
                self.subject
            ),
            "candidate_digest": (
                self.candidate_digest
            ),
            "assurance_digest": (
                self.assurance_digest
            ),
            "decision": (
                self.decision
            ),
            "reason": (
                self.reason
            ),
            "evidence_ids": list(
                self.evidence_ids
            ),
            "provenance": (
                self.provenance
            ),
            "lineage": (
                self.lineage
            ),
            "dependencies": list(
                self.dependencies
            ),
        }

        return (
            "notary-evidence:"
            + digest(
                material
            )[:32]
        )

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "evidence_id": (
                self.evidence_id
            ),
            "subject": (
                self.subject
            ),
            "candidate_digest": (
                self.candidate_digest
            ),
            "assurance_digest": (
                self.assurance_digest
            ),
            "verification_decision": (
                self.decision
            ),
            "verification_reason": (
                self.reason
            ),
            "verified": (
                self.verified
            ),
            "evidence_admitted": (
                self.admitted
            ),
            "evidence_ids": list(
                self.evidence_ids
            ),
            "provenance": (
                self.provenance
            ),
            "lineage": (
                self.lineage
            ),
            "dependencies": list(
                self.dependencies
            ),
            "owner": OWNER,
            "mechanics_owner": (
                MECHANICS_OWNER
            ),
            "attested": False,
            "authority_created": False,
            "authority_mutated": False,
            "authoritative": False,
            "authority_effect": "none",
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def _require_mapping(
    value: Any,
    name: str,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise EvidenceAdmissionError(
            f"{name} must be a mapping"
        )

    return value


def admit_assured_candidate(
    assurance_projection: Mapping[
        str,
        Any,
    ],
    *,
    evidence_ids: Sequence[Any] = (),
    reason: str = (
        "Notary admitted candidate after "
        "successful assurance."
    ),
) -> EvidenceAdmissionDecision:
    projection = _require_mapping(
        assurance_projection,
        "assurance_projection",
    )

    owner = normalize_text(
        projection.get(
            "owner"
        )
    )

    if owner != OWNER:
        raise EvidenceAdmissionError(
            "assurance projection is not "
            "owned by Notary"
        )

    if (
        projection.get(
            "assurance_passed"
        )
        is not True
    ):
        raise EvidenceAdmissionError(
            "failed assurance cannot be "
            "admitted as evidence"
        )

    if (
        projection.get(
            "verification_decision"
        )
        is not None
    ):
        raise EvidenceAdmissionError(
            "assurance projection already "
            "contains verification judgment"
        )

    if (
        projection.get(
            "evidence_admitted"
        )
        is not False
    ):
        raise EvidenceAdmissionError(
            "assurance projection already "
            "claims evidence admission"
        )

    candidate = _require_mapping(
        projection.get(
            "candidate"
        ),
        "candidate",
    )

    assurance = _require_mapping(
        projection.get(
            "assurance"
        ),
        "assurance",
    )

    subject = normalize_text(
        candidate.get(
            "subject"
        )
    )

    if not subject:
        raise EvidenceAdmissionError(
            "candidate subject is required"
        )

    candidate_digest = (
        normalize_text(
            candidate.get(
                "digest"
            )
        )
    )

    if not candidate_digest:
        raise EvidenceAdmissionError(
            "candidate digest is required"
        )

    assurance_digest = (
        normalize_text(
            assurance.get(
                "digest"
            )
        )
    )

    if not assurance_digest:
        assurance_digest = digest(
            assurance
        )

    dependencies = normalize_terms(
        tuple(
            candidate.get(
                "dependencies"
            )
            or ()
        )
    )

    normalized_evidence_ids = (
        normalize_terms(
            evidence_ids
        )
    )

    if not normalized_evidence_ids:
        normalized_evidence_ids = (
            candidate_digest,
        )

    normalized_reason = (
        normalize_text(
            reason
        )
    )

    if not normalized_reason:
        raise EvidenceAdmissionError(
            "verification reason is required"
        )

    return EvidenceAdmissionDecision(
        subject=subject,
        candidate_digest=(
            candidate_digest
        ),
        assurance_digest=(
            assurance_digest
        ),
        decision="admit",
        reason=normalized_reason,
        evidence_ids=(
            normalized_evidence_ids
        ),
        provenance=(
            candidate.get(
                "provenance"
            )
        ),
        lineage=(
            candidate.get(
                "lineage"
            )
        ),
        dependencies=dependencies,
    )


def reject_assured_candidate(
    assurance_projection: Mapping[
        str,
        Any,
    ],
    *,
    reason: str,
    evidence_ids: Sequence[Any] = (),
) -> EvidenceAdmissionDecision:
    projection = _require_mapping(
        assurance_projection,
        "assurance_projection",
    )

    candidate = _require_mapping(
        projection.get(
            "candidate"
        ),
        "candidate",
    )

    assurance = _require_mapping(
        projection.get(
            "assurance"
        ),
        "assurance",
    )

    subject = normalize_text(
        candidate.get(
            "subject"
        )
    )

    candidate_digest = (
        normalize_text(
            candidate.get(
                "digest"
            )
        )
    )

    if not subject:
        raise EvidenceAdmissionError(
            "candidate subject is required"
        )

    if not candidate_digest:
        raise EvidenceAdmissionError(
            "candidate digest is required"
        )

    normalized_reason = (
        normalize_text(
            reason
        )
    )

    if not normalized_reason:
        raise EvidenceAdmissionError(
            "rejection reason is required"
        )

    assurance_digest = (
        normalize_text(
            assurance.get(
                "digest"
            )
        )
        or digest(
            assurance
        )
    )

    dependencies = normalize_terms(
        tuple(
            candidate.get(
                "dependencies"
            )
            or ()
        )
    )

    return EvidenceAdmissionDecision(
        subject=subject,
        candidate_digest=(
            candidate_digest
        ),
        assurance_digest=(
            assurance_digest
        ),
        decision="reject",
        reason=normalized_reason,
        evidence_ids=normalize_terms(
            evidence_ids
        ),
        provenance=(
            candidate.get(
                "provenance"
            )
        ),
        lineage=(
            candidate.get(
                "lineage"
            )
        ),
        dependencies=dependencies,
    )


def status() -> dict[str, Any]:
    payload = {
        "schema": (
            "savant://runtime/notary/"
            "evidence-admission-status/"
            "1.0.0"
        ),
        "owner": OWNER,
        "mechanics_owner": (
            MECHANICS_OWNER
        ),
        "verification_owner": OWNER,
        "evidence_admission_owner": (
            OWNER
        ),
        "successful_assurance_required": (
            True
        ),
        "explicit_verification_decision": (
            True
        ),
        "immutable_decision_projection": (
            True
        ),
        "attestation_separate": True,
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
