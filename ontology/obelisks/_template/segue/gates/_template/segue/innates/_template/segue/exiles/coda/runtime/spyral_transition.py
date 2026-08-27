#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path("/root/savant-runtime").resolve()

MUTATION_PATH = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/_template/segue/"
      "innates/_template/segue/exiles/coda/runtime/mutation.py"
).resolve()

OWNER = "coda"
PLANNING_OWNER = "living:spyral"

SCHEMA = "savant://runtime/coda/spyral-transition/1.0.0"

AuthorityValidator = Callable[
    [Any],
    Any,
]


class CodaSpyralTransitionError(RuntimeError):
    pass


class AuthorityWitnessRejected(
    CodaSpyralTransitionError
):
    pass


def _load_mutation_module():
    module_name = "coda_runtime_mutation"

    existing = sys.modules.get(
        module_name
    )

    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(
        module_name,
        MUTATION_PATH,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise CodaSpyralTransitionError(
            "unable to load Coda mutation runtime"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        module_name
    ] = module

    try:
        spec.loader.exec_module(
            module
        )
    except Exception:
        sys.modules.pop(
            module_name,
            None,
        )
        raise

    return module


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


def _witness_passed(
    result: Any,
) -> bool:
    if isinstance(
        result,
        Mapping,
    ):
        return bool(
            result.get(
                "passed",
                result.get(
                    "valid",
                    result.get(
                        "current",
                        False,
                    ),
                ),
            )
        )

    return bool(
        result
    )


@dataclass(
    frozen=True,
    slots=True,
)
class CodaCommitReceipt:
    transition_id: str
    subject_id: str
    mutation: Mapping[str, Any]
    authority_validation: Any
    request_digest: str

    def projection(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": (
                "savant://runtime/coda/"
                "spyral-commit-receipt/1.0.0"
            ),
            "owner": OWNER,
            "planning_owner": (
                PLANNING_OWNER
            ),
            "transition_id": (
                self.transition_id
            ),
            "subject_id": (
                self.subject_id
            ),
            "mutation": dict(
                self.mutation
            ),
            "authority_validation": (
                self.authority_validation
            ),
            "request_digest": (
                self.request_digest
            ),
            "mutation_owner": OWNER,
            "commit_owner": OWNER,
            "spyral_executed_mutation": False,
            "spyral_authorized_mutation": False,
            "authority_checked_at_commit": True,
            "authority_effect": "none",
            "authoritative": False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


class CodaSpyralTransition:
    def __init__(
        self,
        *,
        authority_validator: AuthorityValidator,
    ) -> None:
        if not callable(
            authority_validator
        ):
            raise CodaSpyralTransitionError(
                "authority_validator must be callable"
            )

        self.authority_validator = (
            authority_validator
        )

        self.mutation = (
            _load_mutation_module()
        )

    def _validate_request(
        self,
        request: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if not isinstance(
            request,
            Mapping,
        ):
            raise CodaSpyralTransitionError(
                "transition request must be a mapping"
            )

        if (
            request.get(
                "owner"
            )
            != PLANNING_OWNER
        ):
            raise CodaSpyralTransitionError(
                "transition request owner "
                "must be living:spyral"
            )

        if (
            request.get(
                "mutation_owner"
            )
            != OWNER
        ):
            raise CodaSpyralTransitionError(
                "mutation owner must be coda"
            )

        if (
            request.get(
                "spyral_authorizes_mutation"
            )
            is not False
        ):
            raise CodaSpyralTransitionError(
                "Spyral may not authorize mutation"
            )

        if (
            request.get(
                "spyral_executes_mutation"
            )
            is not False
        ):
            raise CodaSpyralTransitionError(
                "Spyral may not execute mutation"
            )

        if (
            request.get(
                "mutation_performed"
            )
            is not False
        ):
            raise CodaSpyralTransitionError(
                "incoming transition must remain non-mutating"
            )

        transition = request.get(
            "transition"
        )

        if not isinstance(
            transition,
            Mapping,
        ):
            raise CodaSpyralTransitionError(
                "transition projection is required"
            )

        if (
            transition.get(
                "mutation_performed"
            )
            is not False
        ):
            raise CodaSpyralTransitionError(
                "transition projection claims mutation"
            )

        if request.get(
            "authority_witness"
        ) is None:
            raise CodaSpyralTransitionError(
                "authority witness is required"
            )

        if not str(
            request.get(
                "path",
                "",
            )
        ).strip():
            raise CodaSpyralTransitionError(
                "mutation path is required"
            )

        return transition

    def commit(
        self,
        request: Mapping[str, Any],
    ) -> CodaCommitReceipt:
        transition = (
            self._validate_request(
                request
            )
        )

        authority_witness = (
            request[
                "authority_witness"
            ]
        )

        try:
            authority_validation = (
                self.authority_validator(
                    authority_witness
                )
            )
        except Exception as exc:
            raise AuthorityWitnessRejected(
                "authority witness validation failed"
            ) from exc

        if not _witness_passed(
            authority_validation
        ):
            raise AuthorityWitnessRejected(
                "authority witness rejected at commit time"
            )

        try:
            mutation = (
                self.mutation.replace_text(
                    str(
                        request[
                            "path"
                        ]
                    ),
                    str(
                        request.get(
                            "content",
                            "",
                        )
                    ),
                    expected_digest=(
                        request.get(
                            "expected_digest"
                        )
                    ),
                    requester=str(
                        request.get(
                            "requester",
                            PLANNING_OWNER,
                        )
                    ),
                    intent=str(
                        request.get(
                            "intent",
                            "spyral planned transition",
                        )
                    ),
                )
            )
        except (
            self.mutation.MutationConflict,
            self.mutation.MutationError,
        ) as exc:
            raise CodaSpyralTransitionError(
                str(exc)
            ) from exc

        return CodaCommitReceipt(
            transition_id=str(
                request.get(
                    "transition_id",
                    transition.get(
                        "transition_id",
                        "",
                    ),
                )
            ),
            subject_id=str(
                request.get(
                    "subject_id",
                    transition.get(
                        "subject_id",
                        "",
                    ),
                )
            ),
            mutation=mutation,
            authority_validation=(
                authority_validation
            ),
            request_digest=str(
                request.get(
                    "digest",
                    digest(
                        request
                    ),
                )
            ),
        )

    def status(
        self,
    ) -> dict[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner": OWNER,
            "planning_owner": (
                PLANNING_OWNER
            ),
            "mutation_owner": OWNER,
            "commit_owner": OWNER,
            "authority_validation_owner": OWNER,
            "authority_validator_bound": True,
            "authority_checked_at_commit": True,
            "spyral_plans": True,
            "spyral_authorizes_mutation": False,
            "spyral_executes_mutation": False,
            "coda_authorizes_commit": True,
            "coda_executes_mutation": True,
            "optimistic_concurrency": True,
            "atomic_mutation": True,
            "digest_verification": True,
            "mutation_receipts": True,
            "authority_effect": "none",
            "authoritative": False,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload


def bind_spyral(
    *,
    authority_validator: AuthorityValidator,
) -> CodaSpyralTransition:
    return CodaSpyralTransition(
        authority_validator=(
            authority_validator
        )
    )


def main() -> int:
    runtime = bind_spyral(
        authority_validator=(
            lambda witness: {
                "passed": (
                    isinstance(
                        witness,
                        Mapping,
                    )
                    and witness.get(
                        "current"
                    )
                    is True
                )
            }
        )
    )

    status = runtime.status()

    print(
        json.dumps(
            status,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=str,
        )
    )

    return (
        0
        if (
            status[
                "spyral_authorizes_mutation"
            ]
            is False
            and status[
                "spyral_executes_mutation"
            ]
            is False
            and status[
                "coda_executes_mutation"
            ]
            is True
            and status[
                "authority_checked_at_commit"
            ]
            is True
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
