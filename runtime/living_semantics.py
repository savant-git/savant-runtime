#!/usr/bin/env python3

from __future__ import annotations

import fnmatch
import json
import re

from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


from runtime.living_governance import (
    append_event,
    authority_order,
    canonical_json,
    next_version,
    project,
    projection_digest,
    read_events,
    resolved_records,
    sha256_text,
    stream_records,
    utc_now,
)


schema = "savant.living-semantics.v1"

semantic_streams = frozenset(
    {
        "rules",
        "permissions",
        "invariants",
        "policies",
        "decisions",
        "unknowns",
        "risks",
        "compatibility",
        "dependencies",
        "milestones",
        "masterplan",
        "structure",
        "terminology",
        "evidence",
        "assumptions",
        "hypotheses",
        "contradictions",
        "conclusions",
        "blockers",
    }
)

record_types = frozenset(
    {
        "rule",
        "permission",
        "invariant",
        "policy",
        "decision",
        "unknown",
        "risk",
        "compatibility",
        "dependency",
        "milestone",
        "task",
        "structure",
        "terminology",
        "evidence",
        "assumption",
        "hypothesis",
        "contradiction",
        "conclusion",
        "blocker",
    }
)

effects = frozenset(
    {
        "allow",
        "deny",
        "conditional",
        "advisory",
        "warn",
        "require-authority",
        "observe",
        "none",
    }
)

enforcement_modes = frozenset(
    {
        "advisory",
        "warn",
        "block",
        "require-authority",
        "observe",
    }
)

epistemic_states = frozenset(
    {
        "fact",
        "assertion",
        "inference",
        "estimate",
        "speculation",
        "unknown",
        "projection",
    }
)

evaluation_states = frozenset(
    {
        "pass",
        "fail",
        "advisory",
        "unknown",
        "authority-required",
        "not-applicable",
    }
)

terminal_statuses = frozenset(
    {
        "withdrawn",
        "superseded",
        "inactive",
        "revoked",
    }
)


class living_semantics_error(
    RuntimeError
):
    pass


class semantic_validation_error(
    living_semantics_error
):
    pass


class semantic_not_found(
    living_semantics_error
):
    pass


def _string(
    value: Any,
) -> str:
    return str(
        value
        if value is not None
        else ""
    ).strip()


def _string_list(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        value = [
            value
        ]

    if not isinstance(
        value,
        list,
    ):
        raise semantic_validation_error(
            "expected string or list"
        )

    return sorted(
        {
            _string(
                item
            )
            for item in value
            if _string(
                item
            )
        }
    )


def _mapping(
    value: Any,
) -> dict[str, Any]:
    if value is None:
        return {}

    if not isinstance(
        value,
        Mapping,
    ):
        raise semantic_validation_error(
            "expected object"
        )

    return {
        str(
            key
        ):
            item
        for key, item
        in value.items()
    }


def _timestamp(
    value: str | None,
) -> datetime | None:
    if not value:
        return None

    text = value.strip()

    if text.endswith(
        "Z"
    ):
        text = (
            text[
                :-1
            ]
            + "+00:00"
        )

    try:
        parsed = datetime.fromisoformat(
            text
        )

    except ValueError as exc:
        raise semantic_validation_error(
            (
                "invalid timestamp: "
                + value
            )
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def _canonical_timestamp(
    value: str | None,
) -> str | None:
    parsed = _timestamp(
        value
    )

    if parsed is None:
        return None

    return (
        parsed.replace(
            microsecond=0
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def semantic_uri(
    stream: str,
    semantic_id: str,
    version: int,
) -> str:
    return (
        "savant://governance/"
        + stream
        + "/"
        + semantic_id
        + "@"
        + str(
            version
        )
    )


def normalize_scope(
    value: Any,
) -> dict[str, list[str]]:
    source = _mapping(
        value
    )

    supported = (
        "actors",
        "callers",
        "actions",
        "paths",
        "subsystems",
        "environments",
        "mutation_types",
        "versions",
        "targets",
        "subjects",
    )

    output = {}

    for name in supported:
        values = _string_list(
            source.get(
                name
            )
        )

        if values:
            output[
                name
            ] = values

    return output


def normalize_predicate(
    value: Any,
) -> dict[str, Any]:
    if value is None:
        return {}

    predicate = _mapping(
        value
    )

    operator = _string(
        predicate.get(
            "op"
        )
    )

    if not operator:
        raise semantic_validation_error(
            "predicate op is required"
        )

    supported = {
        "exists",
        "equals",
        "not-equals",
        "in",
        "not-in",
        "contains",
        "starts-with",
        "ends-with",
        "matches",
        "all",
        "any",
        "not",
    }

    if operator not in supported:
        raise semantic_validation_error(
            (
                "unsupported predicate op: "
                + operator
            )
        )

    normalized = {
        "op":
            operator
    }

    if "path" in predicate:
        normalized[
            "path"
        ] = _string(
            predicate.get(
                "path"
            )
        )

    if "value" in predicate:
        normalized[
            "value"
        ] = predicate[
            "value"
        ]

    if operator in {
        "all",
        "any",
    }:
        children = predicate.get(
            "predicates"
        )

        if not isinstance(
            children,
            list,
        ):
            raise semantic_validation_error(
                (
                    operator
                    + " requires predicates"
                )
            )

        normalized[
            "predicates"
        ] = [
            normalize_predicate(
                child
            )
            for child
            in children
        ]

    if operator == "not":
        normalized[
            "predicate"
        ] = normalize_predicate(
            predicate.get(
                "predicate"
            )
        )

    return normalized


def normalize_completion(
    value: Any,
) -> dict[str, Any]:
    completion = _mapping(
        value
    )

    if not completion:
        return {}

    evidence = _string_list(
        completion.get(
            "evidence"
        )
    )

    return {
        "claimed":
            bool(
                completion.get(
                    "claimed",
                    False,
                )
            ),

        "proven":
            bool(
                completion.get(
                    "proven",
                    False,
                )
            ),

        "criteria":
            _string_list(
                completion.get(
                    "criteria"
                )
            ),

        "evidence":
            evidence,

        "receipt":
            _string(
                completion.get(
                    "receipt"
                )
            )
            or None,
    }


def normalize_semantics(
    value: Mapping[str, Any] | None,
    *,
    stream: str,
    semantic_id: str,
    version: int,
) -> dict[str, Any]:
    source = _mapping(
        value
    )

    record_type = (
        _string(
            source.get(
                "type"
            )
        )
        or (
            "task"
            if stream
            == "masterplan"
            else stream.rstrip(
                "s"
            )
        )
    )

    if (
        record_type
        not in record_types
    ):
        raise semantic_validation_error(
            (
                "unknown semantic type: "
                + record_type
            )
        )

    effect = (
        _string(
            source.get(
                "effect"
            )
        )
        or "none"
    )

    if effect not in effects:
        raise semantic_validation_error(
            (
                "unknown effect: "
                + effect
            )
        )

    enforcement = (
        _string(
            source.get(
                "enforcement"
            )
        )
        or "observe"
    )

    if (
        enforcement
        not in enforcement_modes
    ):
        raise semantic_validation_error(
            (
                "unknown enforcement mode: "
                + enforcement
            )
        )

    epistemic_state = (
        _string(
            source.get(
                "epistemic_state"
            )
        )
        or "assertion"
    )

    if (
        epistemic_state
        not in epistemic_states
    ):
        raise semantic_validation_error(
            (
                "unknown epistemic state: "
                + epistemic_state
            )
        )

    confidence_value = source.get(
        "confidence"
    )

    confidence = (
        None
        if confidence_value is None
        else float(
            confidence_value
        )
    )

    if (
        confidence is not None
        and not (
            0.0
            <= confidence
            <= 1.0
        )
    ):
        raise semantic_validation_error(
            (
                "confidence must be "
                "between 0 and 1"
            )
        )

    validity = _mapping(
        source.get(
            "validity"
        )
    )

    effective_from = (
        _canonical_timestamp(
            _string(
                validity.get(
                    "effective_from"
                )
            )
            or None
        )
    )

    effective_until = (
        _canonical_timestamp(
            _string(
                validity.get(
                    "effective_until"
                )
            )
            or None
        )
    )

    if (
        effective_from
        and effective_until
        and _timestamp(
            effective_from
        )
        > _timestamp(
            effective_until
        )
    ):
        raise semantic_validation_error(
            (
                "effective_from occurs "
                "after effective_until"
            )
        )

    output = {
        "schema":
            schema,

        "type":
            record_type,

        "uri":
            semantic_uri(
                stream,
                semantic_id,
                version,
            ),

        "namespace":
            _string(
                source.get(
                    "namespace"
                )
            )
            or "savant",

        "scope":
            normalize_scope(
                source.get(
                    "scope"
                )
            ),

        "subject":
            _string(
                source.get(
                    "subject"
                )
            )
            or None,

        "target":
            _string(
                source.get(
                    "target"
                )
            )
            or None,

        "action":
            _string(
                source.get(
                    "action"
                )
            )
            or None,

        "predicate":
            normalize_predicate(
                source.get(
                    "predicate"
                )
            ),

        "effect":
            effect,

        "enforcement":
            enforcement,

        "specificity":
            int(
                source.get(
                    "specificity",
                    0,
                )
            ),

        "epistemic_state":
            epistemic_state,

        "confidence":
            confidence,

        "evidence_requirements":
            _string_list(
                source.get(
                    "evidence_requirements"
                )
            ),

        "evidence":
            _string_list(
                source.get(
                    "evidence"
                )
            ),

        "exceptions":
            _string_list(
                source.get(
                    "exceptions"
                )
            ),

        "validity":
            {
                "effective_from":
                    effective_from,

                "effective_until":
                    effective_until,
            },

        "reason_code":
            _string(
                source.get(
                    "reason_code"
                )
            )
            or None,

        "reason":
            _string(
                source.get(
                    "reason"
                )
            )
            or None,

        "remediation":
            _string(
                source.get(
                    "remediation"
                )
            )
            or None,

        "tags":
            _string_list(
                source.get(
                    "tags"
                )
            ),

        "completion":
            normalize_completion(
                source.get(
                    "completion"
                )
            ),
    }

    return output


def semantic_record(
    *,
    stream: str,
    semantic_id: str,
    text: str,
    authority: str,
    priority: int,
    status: str,
    supersedes: Iterable[str],
    dependencies: Iterable[str],
    relationships: Iterable[
        Mapping[
            str,
            str,
        ]
    ],
    provenance: Mapping[str, Any],
    semantics: Mapping[str, Any] | None,
    version: int,
) -> dict[str, Any]:
    if stream not in semantic_streams:
        raise semantic_validation_error(
            (
                "unsupported semantic stream: "
                + stream
            )
        )

    if authority not in authority_order:
        raise semantic_validation_error(
            (
                "unknown authority class: "
                + authority
            )
        )

    if not semantic_id:
        raise semantic_validation_error(
            "semantic id is required"
        )

    if semantic_id != semantic_id.lower():
        raise semantic_validation_error(
            (
                "semantic id must be lowercase: "
                + semantic_id
            )
        )

    if not text.strip():
        raise semantic_validation_error(
            "text is required"
        )

    relation_values = []

    for relationship in relationships:
        kind = _string(
            relationship.get(
                "kind"
            )
        )

        target = _string(
            relationship.get(
                "target"
            )
        )

        if (
            not kind
            or not target
        ):
            raise semantic_validation_error(
                (
                    "relationship requires "
                    "kind and target"
                )
            )

        relation_values.append(
            {
                "kind":
                    kind,

                "target":
                    target,
            }
        )

    return {
        "schema":
            "savant.living-governance.v1",

        "id":
            semantic_id,

        "stream":
            stream,

        "version":
            int(
                version
            ),

        "status":
            status,

        "authority":
            authority,

        "authority_rank":
            authority_order[
                authority
            ],

        "priority":
            int(
                priority
            ),

        "text":
            text.strip(),

        "supersedes":
            sorted(
                {
                    _string(
                        item
                    )
                    for item
                    in supersedes
                    if _string(
                        item
                    )
                }
            ),

        "dependencies":
            sorted(
                {
                    _string(
                        item
                    )
                    for item
                    in dependencies
                    if _string(
                        item
                    )
                }
            ),

        "relationships":
            sorted(
                relation_values,
                key=lambda item: (
                    item[
                        "kind"
                    ],
                    item[
                        "target"
                    ],
                ),
            ),

        "provenance":
            dict(
                provenance
            ),

        "semantics":
            normalize_semantics(
                semantics,
                stream=stream,
                semantic_id=
                    semantic_id,
                version=version,
            ),
    }


def assert_semantic(
    *,
    stream: str,
    semantic_id: str,
    text: str,
    semantics: Mapping[str, Any] | None,
    authority: str =
        "current_user_directive",
    priority: int = 1000,
    status: str = "active",
    supersedes: Iterable[str] = (),
    dependencies: Iterable[str] = (),
    relationships: Iterable[
        Mapping[
            str,
            str,
        ]
    ] = (),
    asserted_by: str = "user",
    sources: Iterable[str] = (),
) -> dict[str, Any]:
    version = next_version(
        stream,
        semantic_id,
    )

    provenance = {
        "asserted_by":
            asserted_by,

        "method":
            "living-semantic-assertion",

        "sources":
            sorted(
                {
                    _string(
                        item
                    )
                    for item
                    in sources
                    if _string(
                        item
                    )
                }
            ),

        "created_at":
            utc_now(),
    }

    record = semantic_record(
        stream=stream,
        semantic_id=semantic_id,
        text=text,
        authority=authority,
        priority=priority,
        status=status,
        supersedes=supersedes,
        dependencies=dependencies,
        relationships=relationships,
        provenance=provenance,
        semantics=semantics,
        version=version,
    )

    event = append_event(
        record
    )

    project()

    return event


def current_record(
    stream: str,
    semantic_id: str,
) -> dict[str, Any]:
    for record in stream_records(
        stream
    ):
        if record.get(
            "id"
        ) == semantic_id:
            return dict(
                record
            )

    raise semantic_not_found(
        (
            stream
            + ":"
            + semantic_id
        )
    )


def evolve_semantic(
    *,
    stream: str,
    semantic_id: str,
    text: str | None = None,
    semantics: Mapping[str, Any] | None = None,
    status: str | None = None,
    asserted_by: str = "user",
    sources: Iterable[str] = (),
) -> dict[str, Any]:
    current = current_record(
        stream,
        semantic_id,
    )

    current_semantics = dict(
        current.get(
            "semantics",
            {}
        )
    )

    if semantics:
        current_semantics.update(
            semantics
        )

    return assert_semantic(
        stream=stream,
        semantic_id=semantic_id,
        text=(
            text
            if text is not None
            else str(
                current[
                    "text"
                ]
            )
        ),
        semantics=current_semantics,
        authority=
            "current_user_directive",
        priority=int(
            current.get(
                "priority",
                1000,
            )
        ),
        status=(
            status
            if status is not None
            else str(
                current.get(
                    "status",
                    "active",
                )
            )
        ),
        supersedes=[
            semantic_id
        ],
        dependencies=current.get(
            "dependencies",
            [],
        ),
        relationships=current.get(
            "relationships",
            [],
        ),
        asserted_by=asserted_by,
        sources=sources,
    )


def revoke_semantic(
    *,
    stream: str,
    semantic_id: str,
    reason: str,
    asserted_by: str = "user",
    sources: Iterable[str] = (),
) -> dict[str, Any]:
    current = current_record(
        stream,
        semantic_id,
    )

    semantics = dict(
        current.get(
            "semantics",
            {}
        )
    )

    semantics[
        "reason"
    ] = reason

    semantics[
        "reason_code"
    ] = (
        semantics.get(
            "reason_code"
        )
        or "governance.revoked"
    )

    return evolve_semantic(
        stream=stream,
        semantic_id=semantic_id,
        semantics=semantics,
        status="revoked",
        asserted_by=asserted_by,
        sources=sources,
    )


def _context_value(
    context: Mapping[str, Any],
    path: str,
) -> tuple[
    bool,
    Any,
]:
    if not path:
        return (
            False,
            None,
        )

    current: Any = context

    for part in path.split(
        "."
    ):
        if not isinstance(
            current,
            Mapping,
        ):
            return (
                False,
                None,
            )

        if part not in current:
            return (
                False,
                None,
            )

        current = current[
            part
        ]

    return (
        True,
        current,
    )


def evaluate_predicate(
    predicate: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    if not predicate:
        return {
            "state":
                "pass",

            "reason_code":
                "predicate.none",
        }

    op = _string(
        predicate.get(
            "op"
        )
    )

    if op in {
        "all",
        "any",
    }:
        children = [
            evaluate_predicate(
                child,
                context,
            )
            for child
            in predicate.get(
                "predicates",
                []
            )
        ]

        if op == "all":
            if any(
                child[
                    "state"
                ]
                == "fail"
                for child
                in children
            ):
