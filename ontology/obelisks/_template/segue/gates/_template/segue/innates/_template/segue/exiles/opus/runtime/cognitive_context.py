#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Sequence


def _stable_hash(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _clean_mapping(
    value: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    return dict(value or {})


def _clean_sequence(
    value: Sequence[Mapping[str, Any]] | None,
) -> list[Dict[str, Any]]:
    return [
        dict(item)
        for item in value or ()
        if isinstance(item, Mapping)
    ]


@dataclass(frozen=True)
class CognitiveContext:
    authority: Mapping[str, Any]
    lexicon: Mapping[str, Any]
    kindred: Mapping[str, Any]
    evidence: tuple[Mapping[str, Any], ...]
    projections: tuple[Mapping[str, Any], ...]
    unresolved_conflicts: tuple[Mapping[str, Any], ...]
    context_hash: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "authority": dict(self.authority),
            "lexicon": dict(self.lexicon),
            "kindred": dict(self.kindred),
            "evidence": [
                dict(value)
                for value in self.evidence
            ],
            "projections": [
                dict(value)
                for value in self.projections
            ],
            "unresolved_conflicts": [
                dict(value)
                for value
                in self.unresolved_conflicts
            ],
            "context_hash": self.context_hash,
        }


def build_context(
    *,
    authority: Mapping[str, Any] | None = None,
    lexicon: Mapping[str, Any] | None = None,
    kindred: Mapping[str, Any] | None = None,
    evidence: Sequence[
        Mapping[str, Any]
    ] | None = None,
    projections: Sequence[
        Mapping[str, Any]
    ] | None = None,
    unresolved_conflicts: Sequence[
        Mapping[str, Any]
    ] | None = None,
) -> CognitiveContext:
    body = {
        "authority": _clean_mapping(authority),
        "lexicon": _clean_mapping(lexicon),
        "kindred": _clean_mapping(kindred),
        "evidence": _clean_sequence(evidence),
        "projections": _clean_sequence(
            projections
        ),
        "unresolved_conflicts":
            _clean_sequence(
                unresolved_conflicts
            ),
    }

    return CognitiveContext(
        authority=body["authority"],
        lexicon=body["lexicon"],
        kindred=body["kindred"],
        evidence=tuple(body["evidence"]),
        projections=tuple(
            body["projections"]
        ),
        unresolved_conflicts=tuple(
            body["unresolved_conflicts"]
        ),
        context_hash=_stable_hash(body),
    )


def context_from_request(
    request: Mapping[str, Any],
) -> CognitiveContext:
    context = request.get(
        "cognitive_context"
    )

    if not isinstance(context, Mapping):
        context = {}

    return build_context(
        authority=(
            context.get("authority")
            if isinstance(
                context.get("authority"),
                Mapping,
            )
            else {}
        ),
        lexicon=(
            context.get("lexicon")
            if isinstance(
                context.get("lexicon"),
                Mapping,
            )
            else {}
        ),
        kindred=(
            context.get("kindred")
            if isinstance(
                context.get("kindred"),
                Mapping,
            )
            else {}
        ),
        evidence=(
            context.get("evidence")
            if isinstance(
                context.get("evidence"),
                Sequence,
            )
            and not isinstance(
                context.get("evidence"),
                (str, bytes, bytearray),
            )
            else ()
        ),
        projections=(
            context.get("projections")
            if isinstance(
                context.get("projections"),
                Sequence,
            )
            and not isinstance(
                context.get("projections"),
                (str, bytes, bytearray),
            )
            else ()
        ),
        unresolved_conflicts=(
            context.get(
                "unresolved_conflicts"
            )
            if isinstance(
                context.get(
                    "unresolved_conflicts"
                ),
                Sequence,
            )
            and not isinstance(
                context.get(
                    "unresolved_conflicts"
                ),
                (str, bytes, bytearray),
            )
            else ()
        ),
    )


def inject_context(
    request: Mapping[str, Any],
    context: CognitiveContext,
) -> Dict[str, Any]:
    output = dict(request)

    output["cognitive_context"] = (
        context.as_dict()
    )

    output[
        "authority_sensitive"
    ] = bool(
        context.authority
        or context.unresolved_conflicts
        or request.get(
            "authority_sensitive"
        )
    )

    output[
        "requires_relationship_reasoning"
    ] = bool(
        context.kindred
        or request.get(
            "requires_relationship_reasoning"
        )
    )

    output[
        "requires_historical_reconciliation"
    ] = bool(
        context.lexicon
        or request.get(
            "requires_historical_reconciliation"
        )
    )

    return output
