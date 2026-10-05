#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

from descent_policy import (
    DescentPolicy,
)
from role_calculus import (
    KindredRoleError,
)


class PropagationDisposition(str, Enum):
    PROPAGATE = "propagate"
    BLOCK = "block"
    CONDITIONAL = "conditional"


class PropagationPayload(str, Enum):
    QUALIFICATION = "qualification"
    CHARACTERISTIC = "characteristic"
    CAPABILITY = "capability"
    STATE = "state"
    METADATA = "metadata"


@dataclass(
    frozen=True,
    slots=True,
)
class PropagationPolicy:
    policy_id: str
    payload: PropagationPayload
    disposition: PropagationDisposition
    requires_descent_eligibility: bool
    requires_explicit_evidence: bool
    preserves_source_provenance: bool
    permits_transitive_propagation: bool
    authority: str
    provenance: Mapping[str, Any]
    extensions: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id":
                self.policy_id,
            "payload":
                self.payload.value,
            "disposition":
                self.disposition.value,
            "requires_descent_eligibility":
                self.requires_descent_eligibility,
            "requires_explicit_evidence":
                self.requires_explicit_evidence,
            "preserves_source_provenance":
                self.preserves_source_provenance,
            "permits_transitive_propagation":
                self.permits_transitive_propagation,
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
class PropagationDecision:
    policy_id: str
    payload: PropagationPayload
    permitted: bool
    descent_policy_id: str | None
    source_instance: str
    target_instance: str
    evidence_ids: tuple[str, ...]
    reason: str
    authoritative: bool = False

    def certificate(self) -> dict[str, Any]:
        return {
            "policy_id":
                self.policy_id,
            "payload":
                self.payload.value,
            "permitted":
                self.permitted,
            "descent_policy_id":
                self.descent_policy_id,
            "source_instance":
                self.source_instance,
            "target_instance":
                self.target_instance,
            "evidence_ids":
                list(self.evidence_ids),
            "reason":
                self.reason,
            "authoritative":
                self.authoritative,
            "projection":
                "kindred_propagation_decision",
        }


def _stable_policy_id(
    payload: PropagationPayload,
    disposition: PropagationDisposition,
    authority: str,
) -> str:
    encoded = json.dumps(
        {
            "payload":
                payload.value,
            "disposition":
                disposition.value,
            "authority":
                authority,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return (
        "kindred.propagation-policy."
        + sha256(encoded).hexdigest()[:24]
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
    payload: PropagationPayload,
    disposition: PropagationDisposition,
    requires_descent_eligibility: bool = True,
    requires_explicit_evidence: bool = True,
    preserves_source_provenance: bool = True,
    permits_transitive_propagation: bool = False,
    authority: str = "FOUNDATION-008",
    provenance: Mapping[str, Any] | None = None,
    extensions: Mapping[str, Any] | None = None,
) -> PropagationPolicy:
    authority = authority.strip()

    if not authority:
        raise KindredRoleError(
            "propagation policy authority is required"
        )

    return PropagationPolicy(
        policy_id=_stable_policy_id(
            payload,
            disposition,
            authority,
        ),
        payload=payload,
        disposition=disposition,
        requires_descent_eligibility=
            requires_descent_eligibility,
        requires_explicit_evidence=
            requires_explicit_evidence,
        preserves_source_provenance=
            preserves_source_provenance,
        permits_transitive_propagation=
            permits_transitive_propagation,
        authority=authority,
        provenance=dict(
            provenance or {}
        ),
        extensions=dict(
            extensions or {}
        ),
    )


QUALIFICATION_PROPAGATION = policy(
    payload=PropagationPayload.QUALIFICATION,
    disposition=
        PropagationDisposition.CONDITIONAL,
)

CHARACTERISTIC_PROPAGATION = policy(
    payload=PropagationPayload.CHARACTERISTIC,
    disposition=
        PropagationDisposition.CONDITIONAL,
)

CAPABILITY_PROPAGATION = policy(
    payload=PropagationPayload.CAPABILITY,
    disposition=
        PropagationDisposition.CONDITIONAL,
)

STATE_PROPAGATION = policy(
    payload=PropagationPayload.STATE,
    disposition=
        PropagationDisposition.BLOCK,
)

METADATA_PROPAGATION = policy(
    payload=PropagationPayload.METADATA,
    disposition=
        PropagationDisposition.BLOCK,
)


POLICIES = {
    value.payload:
        value
    for value in (
        QUALIFICATION_PROPAGATION,
        CHARACTERISTIC_PROPAGATION,
        CAPABILITY_PROPAGATION,
        STATE_PROPAGATION,
        METADATA_PROPAGATION,
    )
}


def policy_for(
    payload: PropagationPayload,
) -> PropagationPolicy:
    try:
        return POLICIES[
            payload
        ]
    except KeyError as exc:
        raise KindredRoleError(
            "unknown propagation payload: "
            f"{payload}"
        ) from exc


def decide(
    *,
    propagation_policy: PropagationPolicy,
    source_instance: str,
    target_instance: str,
    evidence_ids: Iterable[str],
    descent_policy: DescentPolicy | None = None,
    descent_eligible: bool | None = None,
    explicit_permission: bool | None = None,
) -> PropagationDecision:
    source_instance = source_instance.strip()
    target_instance = target_instance.strip()

    if not source_instance:
        raise KindredRoleError(
            "propagation source is required"
        )

    if not target_instance:
        raise KindredRoleError(
            "propagation target is required"
        )

    if source_instance == target_instance:
        raise KindredRoleError(
            "propagation endpoints must differ"
        )

    evidence = _normalize_evidence(
        evidence_ids
    )

    descent_policy_id = (
        descent_policy.policy_id
        if descent_policy is not None
        else None
    )

    if (
        propagation_policy.requires_explicit_evidence
        and not evidence
    ):
        permitted = False
        reason = "explicit propagation evidence required"

    elif (
        propagation_policy
        .requires_descent_eligibility
        and descent_eligible is not True
    ):
        permitted = False
        reason = "descent eligibility not established"

    elif (
        propagation_policy.disposition
        is PropagationDisposition.BLOCK
    ):
        permitted = False
        reason = "payload propagation blocked by policy"

    elif (
        propagation_policy.disposition
        is PropagationDisposition.CONDITIONAL
        and explicit_permission is not True
    ):
        permitted = False
        reason = "explicit propagation permission required"

    else:
        permitted = True
        reason = "payload propagation permitted"

    return PropagationDecision(
        policy_id=propagation_policy.policy_id,
        payload=propagation_policy.payload,
        permitted=permitted,
        descent_policy_id=descent_policy_id,
        source_instance=source_instance,
        target_instance=target_instance,
        evidence_ids=evidence,
        reason=reason,
    )


def enhancements() -> tuple[str, ...]:
    return (
        "descent_propagation_separation",
        "independent_propagation_policy",
        "qualification_payload_isolation",
        "characteristic_payload_isolation",
        "capability_payload_isolation",
        "state_payload_isolation",
        "metadata_payload_isolation",
        "default_state_propagation_block",
        "default_metadata_propagation_block",
        "explicit_propagation_evidence",
        "explicit_propagation_permission",
        "descent_eligibility_gate",
        "descent_policy_reference_only",
        "no_descent_implies_propagation",
        "no_propagation_implies_descent",
        "non_authoritative_decision_certificate",
        "immutable_propagation_policy",
        "stable_propagation_policy_identity",
        "source_provenance_preservation",
        "transitive_propagation_control",
        "payload_specific_policy",
        "deterministic_propagation_decision",
        "safe_default_blocking",
        "extension_ready_propagation",
        "authority_bound_propagation",
        "no_duplicate_relationship_authority",
    )


def health() -> dict[str, object]:
    return {
        "healthy":
            len(POLICIES) == 5,
        "policy_count":
            len(POLICIES),
        "payloads": [
            value.value
            for value in PropagationPayload
        ],
        "enhancement_count":
            len(enhancements()),
        "descent_equals_propagation":
            False,
        "propagation_equals_descent":
            False,
        "state_default_propagates":
            False,
        "metadata_default_propagates":
            False,
    }
