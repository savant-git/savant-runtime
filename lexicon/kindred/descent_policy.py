#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

from role_calculus import (
    KindredRoleError,
    Qualification,
)


class DescentSemantic(str, Enum):
    BIOLOGICAL = "biological"
    ADOPTIVE = "adoptive"
    FOSTER = "foster"
    LEGAL = "legal"


class DescentEligibility(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    CONDITIONAL = "conditional"


@dataclass(
    frozen=True,
    slots=True,
)
class DescentPolicy:
    policy_id: str
    semantic: DescentSemantic
    qualification: Qualification
    eligibility: DescentEligibility
    contributes_to_biological_descent: bool
    contributes_to_social_descent: bool
    contributes_to_legal_descent: bool
    permits_lateral_derivation: bool
    permits_generational_derivation: bool
    permits_cousin_derivation: bool
    propagates_qualification: bool
    requires_explicit_evidence: bool
    authority: str
    provenance: Mapping[str, Any]
    extensions: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id":
                self.policy_id,
            "semantic":
                self.semantic.value,
            "qualification":
                self.qualification.value,
            "eligibility":
                self.eligibility.value,
            "contributes_to_biological_descent":
                self.contributes_to_biological_descent,
            "contributes_to_social_descent":
                self.contributes_to_social_descent,
            "contributes_to_legal_descent":
                self.contributes_to_legal_descent,
            "permits_lateral_derivation":
                self.permits_lateral_derivation,
            "permits_generational_derivation":
                self.permits_generational_derivation,
            "permits_cousin_derivation":
                self.permits_cousin_derivation,
            "propagates_qualification":
                self.propagates_qualification,
            "requires_explicit_evidence":
                self.requires_explicit_evidence,
            "authority":
                self.authority,
            "provenance":
                dict(self.provenance),
            "extensions":
                dict(self.extensions),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class DescentDecision:
    policy_id: str
    semantic: DescentSemantic
    included: bool
    purpose: str
    evidence_ids: tuple[str, ...]
    reason: str
    authoritative: bool = False

    def certificate(self) -> dict[str, Any]:
        return {
            "policy_id":
                self.policy_id,
            "semantic":
                self.semantic.value,
            "included":
                self.included,
            "purpose":
                self.purpose,
            "evidence_ids":
                list(self.evidence_ids),
            "reason":
                self.reason,
            "authoritative":
                self.authoritative,
            "projection":
                "kindred_descent_policy_decision",
        }


def _stable_policy_id(
    semantic: DescentSemantic,
    qualification: Qualification,
    authority: str,
) -> str:
    payload = json.dumps(
        {
            "semantic":
                semantic.value,
            "qualification":
                qualification.value,
            "authority":
                authority,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return (
        "kindred.descent-policy."
        + sha256(payload).hexdigest()[:24]
    )


def _normalize_evidence(
    values: Iterable[str],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(value).strip()
                for value in values
                if str(value).strip()
            }
        )
    )


def policy(
    *,
    semantic: DescentSemantic,
    qualification: Qualification,
    eligibility: DescentEligibility =
        DescentEligibility.INCLUDE,
    contributes_to_biological_descent: bool,
    contributes_to_social_descent: bool,
    contributes_to_legal_descent: bool,
    permits_lateral_derivation: bool = True,
    permits_generational_derivation: bool = True,
    permits_cousin_derivation: bool = True,
    propagates_qualification: bool = True,
    requires_explicit_evidence: bool = True,
    authority: str = "FOUNDATION-008",
    provenance: Mapping[str, Any] | None = None,
    extensions: Mapping[str, Any] | None = None,
) -> DescentPolicy:
    if not authority.strip():
        raise KindredRoleError(
            "descent policy authority is required"
        )

    return DescentPolicy(
        policy_id=_stable_policy_id(
            semantic,
            qualification,
            authority,
        ),
        semantic=semantic,
        qualification=qualification,
        eligibility=eligibility,
        contributes_to_biological_descent=
            contributes_to_biological_descent,
        contributes_to_social_descent=
            contributes_to_social_descent,
        contributes_to_legal_descent=
            contributes_to_legal_descent,
        permits_lateral_derivation=
            permits_lateral_derivation,
        permits_generational_derivation=
            permits_generational_derivation,
        permits_cousin_derivation=
            permits_cousin_derivation,
        propagates_qualification=
            propagates_qualification,
        requires_explicit_evidence=
            requires_explicit_evidence,
        authority=authority.strip(),
        provenance=dict(
            provenance or {}
        ),
        extensions=dict(
            extensions or {}
        ),
    )


BIOLOGICAL_DESCENT = policy(
    semantic=DescentSemantic.BIOLOGICAL,
    qualification=Qualification.BIOLOGICAL,
    contributes_to_biological_descent=True,
    contributes_to_social_descent=True,
    contributes_to_legal_descent=False,
)

ADOPTIVE_DESCENT = policy(
    semantic=DescentSemantic.ADOPTIVE,
    qualification=Qualification.ADOPTIVE,
    contributes_to_biological_descent=False,
    contributes_to_social_descent=True,
    contributes_to_legal_descent=True,
)

FOSTER_DESCENT = policy(
    semantic=DescentSemantic.FOSTER,
    qualification=Qualification.FOSTER,
    contributes_to_biological_descent=False,
    contributes_to_social_descent=True,
    contributes_to_legal_descent=False,
    permits_cousin_derivation=False,
)

LEGAL_DESCENT = policy(
    semantic=DescentSemantic.LEGAL,
    qualification=Qualification.LEGAL,
    contributes_to_biological_descent=False,
    contributes_to_social_descent=False,
    contributes_to_legal_descent=True,
)


POLICIES = {
    value.semantic:
        value
    for value in (
        BIOLOGICAL_DESCENT,
        ADOPTIVE_DESCENT,
        FOSTER_DESCENT,
        LEGAL_DESCENT,
    )
}


def policy_for(
    semantic: DescentSemantic,
) -> DescentPolicy:
    try:
        return POLICIES[
            semantic
        ]
    except KeyError as exc:
        raise KindredRoleError(
            "unknown descent semantic: "
            f"{semantic}"
        ) from exc


def qualifies(
    *,
    descent_policy: DescentPolicy,
    purpose: str,
    evidence_ids: Iterable[str],
) -> DescentDecision:
    purpose = purpose.strip()

    if purpose not in {
        "biological",
        "social",
        "legal",
        "lateral",
        "generational",
        "cousin",
    }:
        raise KindredRoleError(
            "unsupported descent-policy purpose: "
            f"{purpose}"
        )

    evidence = _normalize_evidence(
        evidence_ids
    )

    if (
        descent_policy.requires_explicit_evidence
        and not evidence
    ):
        return DescentDecision(
            policy_id=descent_policy.policy_id,
            semantic=descent_policy.semantic,
            included=False,
            purpose=purpose,
            evidence_ids=evidence,
            reason="explicit evidence required",
        )

    if (
        descent_policy.eligibility
        is DescentEligibility.EXCLUDE
    ):
        included = False
        reason = "policy excludes relationship"

    elif purpose == "biological":
        included = (
            descent_policy
            .contributes_to_biological_descent
        )
        reason = (
            "biological descent policy"
            if included
            else "not biological descent"
        )

    elif purpose == "social":
        included = (
            descent_policy
            .contributes_to_social_descent
        )
        reason = (
            "social descent policy"
            if included
            else "not social descent"
        )

    elif purpose == "legal":
        included = (
            descent_policy
            .contributes_to_legal_descent
        )
        reason = (
            "legal descent policy"
            if included
            else "not legal descent"
        )

    elif purpose == "lateral":
        included = (
            descent_policy
            .permits_lateral_derivation
        )
        reason = (
            "lateral derivation permitted"
            if included
            else "lateral derivation excluded"
        )

    elif purpose == "generational":
        included = (
            descent_policy
            .permits_generational_derivation
        )
        reason = (
            "generational derivation permitted"
            if included
            else "generational derivation excluded"
        )

    else:
        included = (
            descent_policy
            .permits_cousin_derivation
        )
        reason = (
            "cousin derivation permitted"
            if included
            else "cousin derivation excluded"
        )

    return DescentDecision(
        policy_id=descent_policy.policy_id,
        semantic=descent_policy.semantic,
        included=included,
        purpose=purpose,
        evidence_ids=evidence,
        reason=reason,
    )


def compatible_path(
    policies: Iterable[DescentPolicy],
    *,
    purpose: str,
    evidence_ids: Iterable[str],
) -> tuple[
    bool,
    tuple[DescentDecision, ...],
]:
    normalized = tuple(
        policies
    )

    if not normalized:
        raise KindredRoleError(
            "descent path requires at least one policy"
        )

    decisions = tuple(
        qualifies(
            descent_policy=value,
            purpose=purpose,
            evidence_ids=evidence_ids,
        )
        for value in normalized
    )

    return (
        all(
            decision.included
            for decision in decisions
        ),
        decisions,
    )


def enhancements() -> tuple[str, ...]:
    return (
        "policy_scoped_descent_semantics",
        "biological_descent_isolation",
        "adoptive_descent_isolation",
        "foster_descent_isolation",
        "legal_descent_isolation",
        "explicit_evidence_gating",
        "purpose_specific_descent_eligibility",
        "lateral_derivation_policy",
        "generational_derivation_policy",
        "cousin_derivation_policy",
        "qualification_propagation_policy",
        "stable_policy_identity",
        "immutable_policy_instances",
        "deterministic_policy_decisions",
        "policy_decision_certificates",
        "non_authoritative_policy_projection",
        "multi_policy_path_validation",
        "social_descent_projection",
        "legal_descent_projection",
        "biological_descent_projection",
        "foster_cousin_exclusion",
        "authority_bound_policy",
        "provenance_ready_policy",
        "extension_ready_policy",
        "no_descent_semantic_conflation",
        "no_guardianship_descent_conflation",
        "no_step_descent_conflation",
        "no_duplicate_relationship_authority",
    )


def health() -> dict[str, object]:
    return {
        "healthy":
            len(POLICIES) == 4,
        "policy_count":
            len(POLICIES),
        "semantics": [
            value.value
            for value in DescentSemantic
        ],
        "enhancement_count":
            len(enhancements()),
        "generic_family_roles_canonical":
            False,
        "guardianship_is_descent":
            False,
        "step_is_descent":
            False,
    }
