#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .engine import (
    Spyral,
    SpyralError,
    Transition,
)


OWNER = "living:spyral"
MUTATION_OWNER = "coda"

SCHEMA = "savant://runtime/spyral/coda-binding/1.0.0"


class SpyralCodaBindingError(RuntimeError):
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
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def normalize_identifier(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


@dataclass(
    frozen=True,
    slots=True,
)
class CodaTransitionRequest:
    transition: Transition
    path: str
    content: str
    expected_digest: str | None
    requester: str
    intent: str
    authority_witness: Any

    def projection(
        self,
    ) -> dict[str, Any]:
        transition = (
            self.transition.projection()
        )

        payload = {
            "schema": (
                "savant://runtime/spyral/"
                "coda-transition-request/1.0.0"
            ),
            "owner": OWNER,
            "mutation_owner": MUTATION_OWNER,
            "transition": transition,
            "transition_id": (
                self.transition.transition_id
            ),
            "subject_id": (
                self.transition.subject_id
            ),
            "path": self.path,
            "content": self.content,
            "expected_digest": (
                self.expected_digest
            ),
            "requester": self.requester,
            "intent": self.intent,
            "authority_witness": (
                self.authority_witness
            ),
            "spyral_authorizes_mutation": False,
            "spyral_executes_mutation": False,
            "coda_must_authorize_commit": True,
            "coda_must_validate_current_authority": True,
            "mutation_performed": False,
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


class SpyralCodaBinding:
    """
    Spyral plans evolution; Coda owns durable mutation.

    This binding can prepare a mutation request from a Spyral
    transition. It never writes files and never authorizes mutation.

    A current authority witness is carried to Coda, which must
    validate it at commit time before mutation.
    """

    def __init__(
        self,
        *,
        spyral: Spyral | None = None,
    ) -> None:
        self.spyral = (
            spyral
            if spyral is not None
            else Spyral()
        )

    def request(
        self,
        *,
        transition: Transition,
        path: str,
        content: str,
        authority_witness: Any,
        expected_digest: str | None = None,
        requester: str = OWNER,
        intent: str = "spyral planned transition",
    ) -> CodaTransitionRequest:
        relative_path = (
            normalize_identifier(path)
        )

        normalized_requester = (
            normalize_identifier(requester)
        )

        normalized_intent = (
            normalize_identifier(intent)
        )

        if not relative_path:
            raise SpyralCodaBindingError(
                "path is required"
            )

        if not normalized_requester:
            raise SpyralCodaBindingError(
                "requester is required"
            )

        if not normalized_intent:
            raise SpyralCodaBindingError(
                "intent is required"
            )

        if authority_witness is None:
            raise SpyralCodaBindingError(
                "current authority witness is required"
            )

        if (
            transition.projection().get(
                "mutation_performed"
            )
            is not False
        ):
            raise SpyralCodaBindingError(
                "Spyral transition must remain "
                "non-mutating"
            )

        return CodaTransitionRequest(
            transition=transition,
            path=relative_path,
            content=str(content),
            expected_digest=(
                expected_digest
            ),
            requester=(
                normalized_requester
            ),
            intent=normalized_intent,
            authority_witness=(
                authority_witness
            ),
        )

    def status(
        self,
    ) -> dict[str, Any]:
        health = self.spyral.health()
        validation = (
            self.spyral.validate()
        )

        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "mutation_owner": (
                MUTATION_OWNER
            ),
            "spyral_health": health,
            "spyral_validation": (
                validation
            ),
            "spyral_plans_transitions": True,
            "spyral_plans_migrations": True,
            "spyral_plans_recovery": True,
            "spyral_executes_mutation": False,
            "spyral_authorizes_mutation": False,
            "coda_owns_durable_mutation": True,
            "authority_witness_required": True,
            "authority_witness_validation_owner": (
                MUTATION_OWNER
            ),
            "commit_owner": MUTATION_OWNER,
            "authority_effect": "none",
            "authoritative": False,
            "rebuildable": True,
        }

        payload["digest"] = digest(
            payload
        )

        return payload


def bind_coda() -> SpyralCodaBinding:
    return SpyralCodaBinding()


def main() -> int:
    binding = bind_coda()

    try:
        transition = (
            binding.spyral.plan(
                subject_id=(
                    "example:subject"
                ),
                baseline={
                    "id": (
                        "example:subject"
                    ),
                    "version": "1.0.0",
                },
                target={
                    "id": (
                        "example:subject"
                    ),
                    "version": "1.1.0",
                },
                migration_steps=(
                    {
                        "operation": (
                            "replace_text"
                        ),
                    },
                ),
                recovery_steps=(
                    {
                        "operation": (
                            "restore_previous"
                        ),
                    },
                ),
                provenance={
                    "source": (
                        "focused-self-check"
                    ),
                },
            )
        )
    except SpyralError as exc:
        raise SpyralCodaBindingError(
            str(exc)
        ) from exc

    request = binding.request(
        transition=transition,
        path=(
            "runtime/spyral/"
            "focused-self-check.txt"
        ),
        content="example\n",
        authority_witness={
            "id": (
                "authority-witness:"
                "focused-self-check"
            ),
            "current": True,
        },
    )

    output = {
        "status": binding.status(),
        "request": (
            request.projection()
        ),
    }

    print(
        json.dumps(
            output,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if (
            output["request"][
                "spyral_executes_mutation"
            ]
            is False
            and output["request"][
                "spyral_authorizes_mutation"
            ]
            is False
            and output["request"][
                "coda_must_authorize_commit"
            ]
            is True
            and output["request"][
                "mutation_performed"
            ]
            is False
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
