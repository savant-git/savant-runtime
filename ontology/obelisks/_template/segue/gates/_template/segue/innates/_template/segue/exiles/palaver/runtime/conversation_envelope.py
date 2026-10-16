#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


schema = (
    "savant://runtime/palaver/"
    "conversation-envelope/1.0.0"
)

owner = "exile:palaver"

persona_owner = "envoy"
provider_owner = "opus"
task_owner = "niche"
context_owner = "scrybe"
canon_owner = "lore/fluid-canon"
mutation_owner = "coda"

maximum_message_characters = 250000
maximum_context_sources = 256
maximum_tool_intents = 128


class conversation_envelope_error(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )


def digest(
    value: Any,
) -> str:
    return sha256(
        canonical_json(
            value
        )
    ).hexdigest()


def nonempty(
    value: Any,
    *,
    name: str,
) -> str:
    normalized = str(
        value
        or ""
    ).strip()

    if not normalized:
        raise (
            conversation_envelope_error(
                f"{name} is required"
            )
        )

    return normalized


def normalized_strings(
    values: Iterable[Any],
    *,
    limit: int,
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()

    for raw in values:
        value = str(
            raw
            or ""
        ).strip()

        if (
            not value
            or value in seen
        ):
            continue

        seen.add(
            value
        )

        result.append(
            value
        )

        if len(
            result
        ) >= limit:
            break

    return tuple(
        result
    )


def normalized_mapping(
    value: Any,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise (
            conversation_envelope_error(
                "expected mapping"
            )
        )

    return {
        str(key):
            item
        for (
            key,
            item,
        ) in value.items()
    }


@dataclass(
    frozen=True,
    slots=True,
)
class envelope_identity:
    session_id: str
    request_id: str

    def projection(
        self,
    ) -> dict[str, str]:
        return {
            "session_id":
                self.session_id,
            "request_id":
                self.request_id,
        }


def semantic_persona(
    persona: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    if not persona:
        raise (
            conversation_envelope_error(
                "persona projection is required"
            )
        )

    if str(
        persona.get(
            "owner"
        )
        or ""
    ).strip().lower() not in {
        "envoy",
        "exile:envoy",
    }:
        raise (
            conversation_envelope_error(
                "persona projection must "
                "be Envoy-owned"
            )
        )

    return {
        "persona_id":
            persona.get(
                "persona_id"
            ),
        "baseline_version":
            persona.get(
                "baseline_version"
            ),
        "composition_digest":
            persona.get(
                "composition_digest"
            ),
        "living_trait_crown":
            list(
                persona.get(
                    "living_trait_crown"
                )
                or ()
            ),
        "capability_gap":
            bool(
                persona.get(
                    "capability_gap",
                    False,
                )
            ),
        "degraded_mode":
            bool(
                persona.get(
                    "degraded_mode",
                    False,
                )
            ),
        "voice_ref":
            persona.get(
                "voice_ref"
            ),
    }


def semantic_context(
    receipt: Mapping[
        str,
        Any,
    ] | None,
) -> dict[str, Any]:
    if not receipt:
        return {
            "receipt_digest":
                None,
            "sources":
                [],
            "projection_only":
                True,
        }

    source_values = (
        receipt.get(
            "sources"
        )
        or receipt.get(
            "source_refs"
        )
        or ()
    )

    sources = normalized_strings(
        source_values,
        limit=
            maximum_context_sources,
    )

    receipt_digest = (
        receipt.get(
            "digest"
        )
        or receipt.get(
            "context_digest"
        )
        or digest(
            receipt
        )
    )

    return {
        "receipt_digest":
            receipt_digest,
        "sources":
            list(
                sources
            ),
        "projection_only":
            True,
    }


def semantic_task(
    binding: Mapping[
        str,
        Any,
    ] | None,
) -> dict[str, Any]:
    if not binding:
        return {
            "task_id":
                None,
            "task_digest":
                None,
        }

    return {
        "task_id":
            binding.get(
                "task_id"
            )
            or binding.get(
                "id"
            ),
        "task_digest":
            binding.get(
                "digest"
            )
            or binding.get(
                "task_digest"
            ),
    }


def semantic_workspace(
    workspace: Mapping[
        str,
        Any,
    ] | None,
) -> dict[str, Any]:
    if not workspace:
        return {}

    allowed = (
        "workspace_id",
        "mode",
        "preset",
        "persona_id",
        "active_module",
        "active_branch_id",
    )

    return {
        key:
            workspace.get(
                key
            )
        for key in allowed
        if key in workspace
    }


def project(
    *,
    session_id: str,
    request_id: str,
    message: str,
    persona: Mapping[
        str,
        Any,
    ],
    context_receipt: Mapping[
        str,
        Any,
    ] | None = None,
    task_binding: Mapping[
        str,
        Any,
    ] | None = None,
    workspace_state: Mapping[
        str,
        Any,
    ] | None = None,
    tool_intents: Iterable[Any] = (),
    parent_request_id: str | None = None,
) -> dict[str, Any]:
    identity = envelope_identity(
        session_id=
            nonempty(
                session_id,
                name="session_id",
            ),
        request_id=
            nonempty(
                request_id,
                name="request_id",
            ),
    )

    normalized_message = str(
        message
        or ""
    )

    if not normalized_message.strip():
        raise (
            conversation_envelope_error(
                "message is required"
            )
        )

    normalized_message = (
        normalized_message[
            :maximum_message_characters
        ]
    )

    persona_projection = (
        semantic_persona(
            normalized_mapping(
                persona
            )
        )
    )

    context_projection = (
        semantic_context(
            normalized_mapping(
                context_receipt
            )
            if context_receipt
            else None
        )
    )

    task_projection = (
        semantic_task(
            normalized_mapping(
                task_binding
            )
            if task_binding
            else None
        )
    )

    workspace_projection = (
        semantic_workspace(
            normalized_mapping(
                workspace_state
            )
            if workspace_state
            else None
        )
    )

    normalized_tools = (
        normalized_strings(
            tool_intents,
            limit=
                maximum_tool_intents,
        )
    )

    parent = (
        str(
            parent_request_id
            or ""
        ).strip()
        or None
    )

    semantic = {
        "identity":
            identity.projection(),
        "parent_request_id":
            parent,
        "message_digest":
            digest(
                normalized_message
            ),
        "persona":
            persona_projection,
        "context":
            context_projection,
        "task":
            task_projection,
        "workspace":
            workspace_projection,
        "tool_intents":
            list(
                normalized_tools
            ),
    }

    envelope_digest = (
        digest(
            semantic
        )
    )

    return {
        "schema":
            schema,
        "owner":
            owner,
        "session_id":
            identity.session_id,
        "request_id":
            identity.request_id,
        "parent_request_id":
            parent,
        "message":
            normalized_message,
        "message_digest":
            semantic[
                "message_digest"
            ],
        "persona":
            persona_projection,
        "persona_projection":
            dict(
                persona
            ),
        "context":
            context_projection,
        "context_receipt":
            (
                dict(
                    context_receipt
                )
                if context_receipt
                else None
            ),
        "task_binding":
            (
                dict(
                    task_binding
                )
                if task_binding
                else None
            ),
        "workspace_state":
            (
                dict(
                    workspace_state
                )
                if workspace_state
                else None
            ),
        "tool_intents":
            list(
                normalized_tools
            ),
        "envelope_digest":
            envelope_digest,
        "semantic_projection":
            semantic,
        "ownership": {
            "conversation":
                owner,
            "persona":
                persona_owner,
            "provider_execution":
                provider_owner,
            "task":
                task_owner,
            "context_projection":
                context_owner,
            "canonical_memory":
                canon_owner,
            "mutation":
                mutation_owner,
        },
        "authority": {
            "authoritative":
                False,
            "projection_only":
                True,
            "creates_authority":
                False,
            "authority_effect":
                "none",
        },
    }


def execution_projection(
    envelope: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:
    if (
        envelope.get(
            "schema"
        )
        != schema
    ):
        raise (
            conversation_envelope_error(
                "invalid conversation envelope"
            )
        )

    persona = envelope.get(
        "persona"
    )

    if not isinstance(
        persona,
        Mapping,
    ):
        raise (
            conversation_envelope_error(
                "missing persona projection"
            )
        )

    return {
        "schema":
            (
                "savant://runtime/palaver/"
                "conversation-execution/1.0.0"
            ),
        "owner":
            owner,
        "session_id":
            envelope.get(
                "session_id"
            ),
        "request_id":
            envelope.get(
                "request_id"
            ),
        "message":
            envelope.get(
                "message"
            ),
        "persona_id":
            persona.get(
                "persona_id"
            ),
        "persona_composition_digest":
            persona.get(
                "composition_digest"
            ),
        "context_receipt_digest":
            (
                envelope.get(
                    "context"
                )
                or {}
            ).get(
                "receipt_digest"
            ),
        "task_id":
            (
                envelope.get(
                    "task_binding"
                )
                or {}
            ).get(
                "task_id"
            )
            if isinstance(
                envelope.get(
                    "task_binding"
                ),
                Mapping,
            )
            else None,
        "tool_intents":
            list(
                envelope.get(
                    "tool_intents"
                )
                or ()
            ),
        "provider_owner":
            provider_owner,
        "conversation_owner":
            owner,
        "persona_owner":
            persona_owner,
        "authority_effect":
            "none",
    }


def replay_equivalent(
    left: Mapping[
        str,
        Any,
    ],
    right: Mapping[
        str,
        Any,
    ],
) -> bool:
    return (
        left.get(
            "envelope_digest"
        )
        == right.get(
            "envelope_digest"
        )
        and left.get(
            "semantic_projection"
        )
        == right.get(
            "semantic_projection"
        )
    )


def status() -> dict[str, Any]:
    return {
        "schema":
            schema,
        "owner":
            owner,
        "purpose":
            "deterministic conversation composition",
        "session_identity":
            True,
        "request_lineage":
            True,
        "persona_receipt_binding":
            True,
        "context_provenance_binding":
            True,
        "task_binding":
            True,
        "workspace_binding":
            True,
        "tool_intent_binding":
            True,
        "semantic_digest":
            True,
        "replay_equivalence":
            True,
        "external_authority":
            False,
        "persistent_authority":
            False,
        "provider_execution":
            False,
        "persona_definition":
            False,
        "task_definition":
            False,
        "canon_definition":
            False,
        "authority_effect":
            "none",
    }


def selftest() -> dict[str, Any]:
    persona = {
        "owner":
            "envoy",
        "persona_id":
            "orobouros",
        "baseline_version":
            1,
        "composition_digest":
            "test-composition",
        "living_trait_crown": [
            "analytical_rigor",
        ],
        "capability_gap":
            False,
        "degraded_mode":
            False,
        "voice_ref":
            "synthetic/palaver_default",
    }

    first = project(
        session_id=
            "palses_test",
        request_id=
            "palreq_test",
        message=
            "test",
        persona=
            persona,
        context_receipt={
            "digest":
                "context-test",
            "sources": [
                "source:a",
            ],
        },
        task_binding={
            "task_id":
                "task:test",
            "digest":
                "task-test",
        },
        workspace_state={
            "mode":
                "single",
        },
        tool_intents=(
            "read",
        ),
    )

    second = project(
        session_id=
            "palses_test",
        request_id=
            "palreq_test",
        message=
            "test",
        persona=
            persona,
        context_receipt={
            "digest":
                "context-test",
            "sources": [
                "source:a",
            ],
        },
        task_binding={
            "task_id":
                "task:test",
            "digest":
                "task-test",
        },
        workspace_state={
            "mode":
                "single",
        },
        tool_intents=(
            "read",
        ),
    )

    if not replay_equivalent(
        first,
        second,
    ):
        raise (
            conversation_envelope_error(
                "deterministic replay failed"
            )
        )

    if (
        first[
            "ownership"
        ][
            "persona"
        ]
        != "envoy"
    ):
        raise (
            conversation_envelope_error(
                "persona ownership violated"
            )
        )

    return {
        "schema":
            schema,
        "ok":
            True,
        "envelope_digest":
            first[
                "envelope_digest"
            ],
        "authority_effect":
            "none",
    }


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )
