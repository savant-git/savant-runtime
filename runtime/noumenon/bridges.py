from __future__ import annotations

from typing import Any, Mapping, Sequence

from runtime.noumenon.integrant import (
    IntegrantEnvelope,
    consume,
    emit,
    request,
)
from runtime.noumenon.state import (
    NoumenonState,
)


def guise_character_projection(
    payload: Mapping[str, Any],
    *,
    evidence_refs: Sequence[str] = (),
    lineage_refs: Sequence[str] = (),
    provenance_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    return consume(
        "guise",
        "character_projection",
        payload,
        evidence_refs=evidence_refs,
        lineage_refs=lineage_refs,
        provenance_refs=provenance_refs,
    )


def rapport_projection(
    payload: Mapping[str, Any],
    *,
    evidence_refs: Sequence[str] = (),
    lineage_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    return consume(
        "rapport",
        "relationship_projection",
        payload,
        evidence_refs=evidence_refs,
        lineage_refs=lineage_refs,
    )


def memory_projection(
    payload: Mapping[str, Any],
    *,
    evidence_refs: Sequence[str] = (),
    lineage_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    return consume(
        "memory",
        "memory_projection",
        payload,
        evidence_refs=evidence_refs,
        lineage_refs=lineage_refs,
    )


def envoy_persona_projection(
    payload: Mapping[str, Any],
    *,
    authority_refs: Sequence[str] = (),
    lineage_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    return consume(
        "envoy",
        "persona_projection",
        payload,
        authority_refs=authority_refs,
        lineage_refs=lineage_refs,
    )


def opus_appraisal_request(
    state: NoumenonState,
    *,
    experience_id: str,
    context_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    return request(
        "opus",
        "noumenon.appraise",
        {
            "schema": (
                "savant://noumenon/"
                "opus-appraisal-request/1"
            ),
            "noumenon_id": state.noumenon_id,
            "state_digest": state.state_digest,
            "generation": state.generation,
            "experience_id": experience_id,
            "context_refs": list(context_refs),
        },
        lineage_refs=(
            state.lineage_refs
            + (state.noumenon_id,)
        ),
    )


def opus_reflection_request(
    state: NoumenonState,
    *,
    question: str,
    context_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    if not question:
        raise ValueError("question is required")

    return request(
        "opus",
        "noumenon.reflect",
        {
            "schema": (
                "savant://noumenon/"
                "opus-reflection-request/1"
            ),
            "noumenon_id": state.noumenon_id,
            "state_digest": state.state_digest,
            "question": question,
            "context_refs": list(context_refs),
        },
        lineage_refs=(
            state.lineage_refs
            + (state.noumenon_id,)
        ),
    )


def underscore_divergence_request(
    state: NoumenonState,
    *,
    candidate_refs: Sequence[str],
) -> IntegrantEnvelope:
    return request(
        "underscore",
        "noumenon.diverge",
        {
            "schema": (
                "savant://noumenon/"
                "underscore-divergence-request/1"
            ),
            "noumenon_id": state.noumenon_id,
            "state_digest": state.state_digest,
            "candidate_refs": list(
                candidate_refs
            ),
            "authority_effect": "none",
        },
        lineage_refs=(
            state.lineage_refs
            + (state.noumenon_id,)
        ),
    )


def carbon_counterlife_request(
    state: NoumenonState,
    *,
    fork_ref: str,
    excluded_event_refs: Sequence[str] = (),
) -> IntegrantEnvelope:
    if not fork_ref:
        raise ValueError("fork_ref is required")

    return request(
        "carbon",
        "noumenon.counterlife",
        {
            "schema": (
                "savant://noumenon/"
                "counterlife-request/1"
            ),
            "noumenon_id": state.noumenon_id,
            "state_digest": state.state_digest,
            "fork_ref": fork_ref,
            "excluded_event_refs": list(
                excluded_event_refs
            ),
            "authoritative": False,
        },
        lineage_refs=(
            state.lineage_refs
            + (state.noumenon_id,)
        ),
    )


def rapport_consequence_candidate(
    state: NoumenonState,
    payload: Mapping[str, Any],
) -> IntegrantEnvelope:
    return emit(
        "rapport",
        "relationship_consequence_candidate",
        {
            "schema": (
                "savant://noumenon/"
                "relationship-consequence/1"
            ),
            "noumenon_id": state.noumenon_id,
            "state_digest": state.state_digest,
            "candidate": dict(payload),
        },
        lineage_refs=state.lineage_refs,
    )


def memory_significance_candidate(
    state: NoumenonState,
    *,
    memory_ref: str,
    significance: float,
) -> IntegrantEnvelope:
    if not memory_ref:
        raise ValueError("memory_ref is required")

    return emit(
        "memory",
        "significance_projection",
        {
            "schema": (
                "savant://noumenon/"
                "memory-significance/1"
            ),
            "noumenon_id": state.noumenon_id,
            "memory_ref": memory_ref,
            "significance": float(significance),
        },
        lineage_refs=state.lineage_refs,
    )


def coda_durable_mutation_candidate(
    state: NoumenonState,
    payload: Mapping[str, Any],
) -> IntegrantEnvelope:
    return emit(
        "coda",
        "durable_mutation_candidate",
        {
            "schema": (
                "savant://noumenon/"
                "durable-mutation/1"
            ),
            "noumenon_id": state.noumenon_id,
            "state_digest": state.state_digest,
            "candidate": dict(payload),
        },
        lineage_refs=state.lineage_refs,
    )
