#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from runtime.translucent.blot_acceptance import (
    AcceptanceDecision,
    decide,
)
from runtime.translucent.blot_projection_lock import (
    ProjectionLock,
    lock,
)
from runtime.translucent.blot_projection_registry import (
    ProjectionEntry,
    ProjectionRegistry,
)
from runtime.translucent.blot_replay import (
    ReplayBinding,
    ReplayResult,
    bind,
    replay,
)
from runtime.translucent.blot_verify import (
    VerificationReport,
    verify_projection,
)


name = "blot."
schema = "savant.translucent.blot.projection-finalize.v1"
authority_effect = "none"
mutation_effect = "none"
projection_only = True


class BlotProjectionFinalizeError(ValueError):
    pass


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise BlotProjectionFinalizeError(
            "value is not canonical-json compatible"
        ) from exc


def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = _canonical(value).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _text(
    value: Any,
    field_name: str,
) -> str:
    result = str(value or "").strip()

    if not result:
        raise BlotProjectionFinalizeError(
            f"{field_name} is required"
        )

    return result


def _mapping(
    value: Any,
    field_name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BlotProjectionFinalizeError(
            f"{field_name} must be a mapping"
        )

    return value


def _unique(
    values: Iterable[Any],
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        token = str(value or "").strip()

        if not token or token in seen:
            continue

        seen.add(token)
        result.append(token)

    return tuple(result)


def _normalized(
    value: Any,
    field_name: str,
) -> dict[str, Any]:
    if hasattr(value, "normalized"):
        result = value.normalized()
    elif isinstance(value, Mapping):
        result = dict(value)
    else:
        raise BlotProjectionFinalizeError(
            f"{field_name} must provide normalized() "
            "or be a mapping"
        )

    if not isinstance(result, Mapping):
        raise BlotProjectionFinalizeError(
            f"{field_name}.normalized() must return a mapping"
        )

    return dict(result)


@dataclass(frozen=True)
class FinalizationRequest:
    svg: str
    document: Mapping[str, Any]
    execution_contract: Mapping[str, Any]
    projection_receipt: Mapping[str, Any]
    profile_id: str
    expected: Mapping[str, Any] | None = None
    dependency_digests: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    projection_id: str | None = None

    def normalized(self) -> dict[str, Any]:
        if not isinstance(self.svg, str) or not self.svg.strip():
            raise BlotProjectionFinalizeError(
                "svg must be non-empty"
            )

        document = dict(
            _mapping(
                self.document,
                "document",
            )
        )

        execution_contract = dict(
            _mapping(
                self.execution_contract,
                "execution_contract",
            )
        )

        projection_receipt = dict(
            _mapping(
                self.projection_receipt,
                "projection_receipt",
            )
        )

        expected = dict(
            self.expected or {}
        )

        profile_id = _text(
            self.profile_id,
            "profile_id",
        )

        projection_id = None

        if self.projection_id is not None:
            projection_id = _text(
                self.projection_id,
                "projection_id",
            )

        body = {
            "svg_digest":
                _digest(self.svg),

            "document":
                document,

            "execution_contract":
                execution_contract,

            "projection_receipt":
                projection_receipt,

            "profile_id":
                profile_id,

            "expected":
                expected,

            "dependency_digests":
                list(
                    _unique(
                        self.dependency_digests
                    )
                ),

            "lineage":
                list(
                    _unique(
                        self.lineage
                    )
                ),

            "provenance":
                list(
                    _unique(
                        self.provenance
                    )
                ),

            "projection_id":
                projection_id,
        }

        return {
            **body,
            "digest":
                _digest(body),
        }


@dataclass(frozen=True)
class FinalizationResult:
    request_digest: str
    verification: VerificationReport
    acceptance: AcceptanceDecision | None
    replay_binding: ReplayBinding | None
    replay_result: ReplayResult | None
    projection_lock: ProjectionLock | None
    projection_entry: ProjectionEntry | None
    finalized: bool

    def normalized(self) -> dict[str, Any]:
        verification = _normalized(
            self.verification,
            "verification",
        )

        acceptance = (
            None
            if self.acceptance is None
            else _normalized(
                self.acceptance,
                "acceptance",
            )
        )

        replay_binding = (
            None
            if self.replay_binding is None
            else _normalized(
                self.replay_binding,
                "replay_binding",
            )
        )

        replay_result = (
            None
            if self.replay_result is None
            else _normalized(
                self.replay_result,
                "replay_result",
            )
        )

        projection_lock = (
            None
            if self.projection_lock is None
            else _normalized(
                self.projection_lock,
                "projection_lock",
            )
        )

        projection_entry = (
            None
            if self.projection_entry is None
            else _normalized(
                self.projection_entry,
                "projection_entry",
            )
        )

        computed_finalized = (
            bool(
                verification.get(
                    "accepted",
                    False,
                )
            )
            and acceptance is not None
            and bool(
                acceptance.get(
                    "accepted",
                    False,
                )
            )
            and replay_binding is not None
            and replay_result is not None
            and bool(
                replay_result.get(
                    "deterministic",
                    False,
                )
            )
            and projection_lock is not None
            and bool(
                projection_lock.get(
                    "locked",
                    False,
                )
            )
            and projection_entry is not None
        )

        if bool(self.finalized) != computed_finalized:
            raise BlotProjectionFinalizeError(
                "finalized state does not match "
                "finalization artifacts"
            )

        body = {
            "schema":
                schema,

            "name":
                name,

            "request_digest":
                _text(
                    self.request_digest,
                    "request_digest",
                ),

            "verification":
                verification,

            "acceptance":
                acceptance,

            "replay_binding":
                replay_binding,

            "replay_result":
                replay_result,

            "projection_lock":
                projection_lock,

            "projection_entry":
                projection_entry,

            "finalized":
                computed_finalized,

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,

            "projection_is_authority":
                False,

            "creates_authority":
                False,
        }

        return {
            **body,
            "digest":
                _digest(body),
        }


class ProjectionFinalizer:
    def __init__(
        self,
        *,
        registry: ProjectionRegistry | None = None,
        failure_router: Any = None,
    ) -> None:
        self.registry = (
            registry
            if registry is not None
            else ProjectionRegistry()
        )

        self.failure_router = failure_router

    def verify(
        self,
        request: FinalizationRequest,
    ) -> VerificationReport:
        request.normalized()

        return verify_projection(
            svg=request.svg,
            document=request.document,
            execution_contract=
                request.execution_contract,
            projection_receipt=
                request.projection_receipt,
            expected=request.expected,
            failure_router=
                self.failure_router,
        )

    def finalize(
        self,
        request: FinalizationRequest,
    ) -> FinalizationResult:
        request_data = request.normalized()

        verification = self.verify(
            request
        )

        verification_data = (
            verification.normalized()
        )

        if not verification_data[
            "accepted"
        ]:
            result = FinalizationResult(
                request_digest=
                    request_data[
                        "digest"
                    ],

                verification=
                    verification,

                acceptance=
                    None,

                replay_binding=
                    None,

                replay_result=
                    None,

                projection_lock=
                    None,

                projection_entry=
                    None,

                finalized=
                    False,
            )

            result.normalized()

            return result

        acceptance = decide(
            verification
        )

        acceptance_data = (
            acceptance.normalized()
        )

        if not acceptance_data[
            "accepted"
        ]:
            raise BlotProjectionFinalizeError(
                "verification accepted but "
                "acceptance decision rejected"
            )

        source_digest = _text(
            verification_data[
                "source_digest"
            ],
            "source_digest",
        )

        construction_digest = _text(
            verification_data[
                "construction_digest"
            ],
            "construction_digest",
        )

        execution_digest = _text(
            verification_data[
                "execution_digest"
            ],
            "execution_digest",
        )

        projection_digest = _text(
            verification_data[
                "projection_digest"
            ],
            "projection_digest",
        )

        actual_projection_digest = (
            _digest(
                request.svg
            )
        )

        if (
            actual_projection_digest
            != projection_digest
        ):
            raise BlotProjectionFinalizeError(
                "verified projection digest does not "
                "match SVG bytes"
            )

        replay_binding = bind(
            source_digest=
                source_digest,

            construction_digest=
                construction_digest,

            execution_digest=
                execution_digest,

            profile_id=
                request.profile_id,

            projection=
                request.svg,

            dependency_digests=
                request.dependency_digests,

            lineage=
                request.lineage,

            provenance=
                request.provenance,
        )

        replay_result = replay(
            replay_binding,
            request.svg,
        )

        replay_data = (
            replay_result.normalized()
        )

        if not replay_data[
            "deterministic"
        ]:
            raise BlotProjectionFinalizeError(
                "projection replay is not deterministic"
            )

        projection_lock = lock(
            verification=
                verification,

            acceptance=
                acceptance,

            replay_binding=
                replay_binding,

            replay_result=
                replay_result,

            profile_id=
                request.profile_id,

            lineage=
                request.lineage,

            provenance=
                request.provenance,
        )

        projection_entry = (
            self.registry.register(
                projection_lock,
                projection_id=
                    request.projection_id,
                lineage=
                    request.lineage,
                provenance=
                    request.provenance,
            )
        )

        result = FinalizationResult(
            request_digest=
                request_data[
                    "digest"
                ],

            verification=
                verification,

            acceptance=
                acceptance,

            replay_binding=
                replay_binding,

            replay_result=
                replay_result,

            projection_lock=
                projection_lock,

            projection_entry=
                projection_entry,

            finalized=
                True,
        )

        result.normalized()

        return result

    def manifest(self) -> dict[str, Any]:
        registry_manifest = (
            self.registry.manifest()
        )

        body = {
            "schema":
                schema,

            "name":
                name,

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,

            "pipeline": [
                "verify",
                "accept",
                "bind-replay",
                "replay",
                "lock",
                "register",
            ],

            "hard_gate":
                "verification-accepted",

            "replay_gate":
                "byte-exact-deterministic",

            "lock_gate":
                (
                    "verification-and-acceptance-"
                    "and-replay"
                ),

            "registry_digest":
                registry_manifest[
                    "digest"
                ],

            "projection_is_authority":
                False,

            "registry_is_authority":
                False,

            "creates_authority":
                False,

            "canonical_source":
                "construction-graph",
        }

        return {
            **body,
            "digest":
                _digest(body),
        }


def finalize_projection(
    *,
    svg: str,
    document: Mapping[str, Any],
    execution_contract: Mapping[str, Any],
    projection_receipt: Mapping[str, Any],
    profile_id: str,
    expected: Mapping[str, Any] | None = None,
    dependency_digests: Iterable[str] = (),
    lineage: Iterable[str] = (),
    provenance: Iterable[str] = (),
    projection_id: str | None = None,
    registry: ProjectionRegistry | None = None,
    failure_router: Any = None,
) -> FinalizationResult:
    request = FinalizationRequest(
        svg=svg,
        document=document,
        execution_contract=
            execution_contract,
        projection_receipt=
            projection_receipt,
        profile_id=profile_id,
        expected=expected,
        dependency_digests=
            tuple(
                dependency_digests
            ),
        lineage=
            tuple(
                lineage
            ),
        provenance=
            tuple(
                provenance
            ),
        projection_id=
            projection_id,
    )

    finalizer = ProjectionFinalizer(
        registry=registry,
        failure_router=failure_router,
    )

    return finalizer.finalize(
        request
    )


def manifest() -> dict[str, Any]:
    body = {
        "schema":
            schema,

        "name":
            name,

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,

        "projection_only":
            projection_only,

        "pipeline": [
            "verify",
            "accept",
            "bind-replay",
            "replay",
            "lock",
            "register",
        ],

        "failure_behavior":
            (
                "verification rejection stops "
                "before acceptance and locking"
            ),

        "determinism":
            "sha256-byte-exact",

        "canonical_source":
            "construction-graph",

        "projection_is_authority":
            False,

        "registry_is_authority":
            False,

        "creates_authority":
            False,

        "deleting_projection_deletes_source":
            False,
    }

    return {
        **body,
        "digest":
            _digest(body),
    }


__all__ = [
    "BlotProjectionFinalizeError",
    "FinalizationRequest",
    "FinalizationResult",
    "ProjectionFinalizer",
    "authority_effect",
    "finalize_projection",
    "manifest",
    "mutation_effect",
    "name",
    "projection_only",
    "schema",
]


if __name__ == "__main__":
    print(
        json.dumps(
            manifest(),
            indent=2,
            sort_keys=True,
        )
    )
