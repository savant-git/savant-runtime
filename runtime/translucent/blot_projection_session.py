#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from runtime.translucent.blot_projection_finalize import (
    FinalizationRequest,
    FinalizationResult,
    ProjectionFinalizer,
)
from runtime.translucent.blot_projection_profiles import (
    ProjectionProfile,
    ProjectionProfileRegistry,
)
from runtime.translucent.blot_projection_registry import (
    ProjectionRegistry,
)
from runtime.translucent.blot_projection_set import (
    ProjectionSet,
    ProjectionSetBuilder,
    canonical_profiles,
)


name = "blot."
schema = "savant.translucent.blot.projection-session.v1"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

construction_owner = "blot."
orchestration_owner = "opus"
projection_owner = "blot."

max_projection_artifacts = 32


class BlotProjectionSessionError(ValueError):
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
        raise BlotProjectionSessionError(
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
        raise BlotProjectionSessionError(
            f"{field_name} is required"
        )

    return result


def _mapping(
    value: Any,
    field_name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BlotProjectionSessionError(
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
        raise BlotProjectionSessionError(
            f"{field_name} must provide normalized() "
            "or be a mapping"
        )

    if not isinstance(result, Mapping):
        raise BlotProjectionSessionError(
            f"{field_name}.normalized() must return a mapping"
        )

    return dict(result)


@dataclass(frozen=True)
class ProjectionArtifact:
    profile_id: str
    svg: str
    document: Mapping[str, Any]
    projection_receipt: Mapping[str, Any]
    expected: Mapping[str, Any] = field(
        default_factory=dict
    )
    dependency_digests: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    projection_id: str | None = None

    def normalized(self) -> dict[str, Any]:
        profile_id = _text(
            self.profile_id,
            "profile_id",
        )

        if not isinstance(self.svg, str) or not self.svg.strip():
            raise BlotProjectionSessionError(
                "svg must be non-empty"
            )

        document = dict(
            _mapping(
                self.document,
                "document",
            )
        )

        projection_receipt = dict(
            _mapping(
                self.projection_receipt,
                "projection_receipt",
            )
        )

        expected = dict(
            _mapping(
                self.expected,
                "expected",
            )
        )

        projection_id = None

        if self.projection_id is not None:
            projection_id = _text(
                self.projection_id,
                "projection_id",
            )

        body = {
            "profile_id":
                profile_id,

            "svg_digest":
                _digest(
                    self.svg
                ),

            "document":
                document,

            "projection_receipt":
                projection_receipt,

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
class ProjectionSessionReceipt:
    source_digest: str
    construction_digest: str
    execution_digest: str
    requested_profiles: tuple[str, ...]
    finalized_profiles: tuple[str, ...]
    rejected_profiles: tuple[str, ...]
    projection_set_digest: str | None
    complete: bool
    result_digests: tuple[str, ...]
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        requested_profiles = _unique(
            self.requested_profiles
        )

        finalized_profiles = _unique(
            self.finalized_profiles
        )

        rejected_profiles = _unique(
            self.rejected_profiles
        )

        if (
            set(finalized_profiles)
            & set(rejected_profiles)
        ):
            raise BlotProjectionSessionError(
                "a profile cannot be both finalized and rejected"
            )

        if not set(
            finalized_profiles
        ).issubset(
            set(requested_profiles)
        ):
            raise BlotProjectionSessionError(
                "finalized profile was not requested"
            )

        if not set(
            rejected_profiles
        ).issubset(
            set(requested_profiles)
        ):
            raise BlotProjectionSessionError(
                "rejected profile was not requested"
            )

        resolved = (
            set(finalized_profiles)
            | set(rejected_profiles)
        )

        if resolved != set(
            requested_profiles
        ):
            raise BlotProjectionSessionError(
                "every requested profile must have a terminal state"
            )

        complete = (
            set(canonical_profiles)
            <= set(finalized_profiles)
        )

        if bool(self.complete) != complete:
            raise BlotProjectionSessionError(
                "session completeness does not match finalized profiles"
            )

        projection_set_digest = (
            None
            if self.projection_set_digest is None
            else _text(
                self.projection_set_digest,
                "projection_set_digest",
            )
        )

        if complete and projection_set_digest is None:
            raise BlotProjectionSessionError(
                "complete session requires projection set digest"
            )

        body = {
            "schema":
                schema,

            "name":
                name,

            "source_digest":
                _text(
                    self.source_digest,
                    "source_digest",
                ),

            "construction_digest":
                _text(
                    self.construction_digest,
                    "construction_digest",
                ),

            "execution_digest":
                _text(
                    self.execution_digest,
                    "execution_digest",
                ),

            "requested_profiles":
                list(
                    requested_profiles
                ),

            "finalized_profiles":
                list(
                    finalized_profiles
                ),

            "rejected_profiles":
                list(
                    rejected_profiles
                ),

            "projection_set_digest":
                projection_set_digest,

            "complete":
                complete,

            "result_digests":
                list(
                    _unique(
                        self.result_digests
                    )
                ),

            "provenance":
                list(
                    _unique(
                        self.provenance
                    )
                ),

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,

            "construction_owner":
                construction_owner,

            "orchestration_owner":
                orchestration_owner,

            "projection_owner":
                projection_owner,

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


@dataclass(frozen=True)
class ProjectionSessionResult:
    receipt: ProjectionSessionReceipt
    projection_set: ProjectionSet | None
    results: tuple[FinalizationResult, ...]

    def normalized(self) -> dict[str, Any]:
        receipt = self.receipt.normalized()

        projection_set = (
            None
            if self.projection_set is None
            else self.projection_set.normalized()
        )

        results = tuple(
            result.normalized()
            for result in self.results
        )

        result_digests = tuple(
            result["digest"]
            for result in results
        )

        if tuple(
            receipt["result_digests"]
        ) != result_digests:
            raise BlotProjectionSessionError(
                "session receipt result digests do not "
                "match finalization results"
            )

        if projection_set is None:
            if receipt[
                "projection_set_digest"
            ] is not None:
                raise BlotProjectionSessionError(
                    "receipt references absent projection set"
                )
        else:
            if (
                receipt[
                    "projection_set_digest"
                ]
                != projection_set[
                    "digest"
                ]
            ):
                raise BlotProjectionSessionError(
                    "projection set digest mismatch"
                )

        body = {
            "schema":
                f"{schema}.result",

            "name":
                name,

            "receipt":
                receipt,

            "projection_set":
                projection_set,

            "results":
                list(results),

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,

            "projection_is_authority":
                False,
        }

        return {
            **body,
            "digest":
                _digest(body),
        }


class ProjectionSession:
    def __init__(
        self,
        *,
        source_digest: str,
        construction_digest: str,
        execution_contract: Mapping[str, Any],
        profiles: ProjectionProfileRegistry | None = None,
        registry: ProjectionRegistry | None = None,
        failure_router: Callable[[str], str] | None = None,
        provenance: Iterable[str] = (),
    ) -> None:
        self.source_digest = _text(
            source_digest,
            "source_digest",
        )

        self.construction_digest = _text(
            construction_digest,
            "construction_digest",
        )

        self.execution_contract = dict(
            _mapping(
                execution_contract,
                "execution_contract",
            )
        )

        self.execution_digest = _text(
            self.execution_contract.get(
                "digest"
            )
            or _digest(
                self.execution_contract
            ),
            "execution_digest",
        )

        contract_construction_digest = str(
            self.execution_contract.get(
                "construction_digest",
                "",
            )
        ).strip()

        if (
            contract_construction_digest
            and contract_construction_digest
            != self.construction_digest
        ):
            raise BlotProjectionSessionError(
                "execution contract construction digest mismatch"
            )

        if not bool(
            self.execution_contract.get(
                "execution_ready",
                False,
            )
        ):
            raise BlotProjectionSessionError(
                "projection session requires execution-ready contract"
            )

        blocking_ambiguities = int(
            self.execution_contract.get(
                "blocking_ambiguities",
                0,
            )
            or 0
        )

        if blocking_ambiguities:
            raise BlotProjectionSessionError(
                "projection session cannot begin with blocking ambiguities"
            )

        self.profiles = (
            profiles
            if profiles is not None
            else ProjectionProfileRegistry()
        )

        self.registry = (
            registry
            if registry is not None
            else ProjectionRegistry()
        )

        self.finalizer = ProjectionFinalizer(
            registry=self.registry,
            failure_router=failure_router,
        )

        self.provenance = _unique(
            provenance
        )

        self._artifacts: dict[
            str,
            ProjectionArtifact,
        ] = {}

        self._results: dict[
            str,
            FinalizationResult,
        ] = {}

    def add_artifact(
        self,
        artifact: ProjectionArtifact,
    ) -> ProjectionArtifact:
        if not isinstance(
            artifact,
            ProjectionArtifact,
        ):
            raise BlotProjectionSessionError(
                "artifact must be ProjectionArtifact"
            )

        if len(
            self._artifacts
        ) >= max_projection_artifacts:
            raise BlotProjectionSessionError(
                "projection artifact limit exceeded"
            )

        data = artifact.normalized()
        profile_id = data[
            "profile_id"
        ]

        self.profiles.get(
            profile_id
        )

        receipt = data[
            "projection_receipt"
        ]

        receipt_source_digest = str(
            receipt.get(
                "source_digest",
                "",
            )
        ).strip()

        if (
            receipt_source_digest
            and receipt_source_digest
            != self.source_digest
        ):
            raise BlotProjectionSessionError(
                "projection artifact source digest mismatch"
            )

        receipt_construction_digest = str(
            receipt.get(
                "construction_digest",
                "",
            )
        ).strip()

        if (
            receipt_construction_digest
            and receipt_construction_digest
            != self.construction_digest
        ):
            raise BlotProjectionSessionError(
                "projection artifact construction digest mismatch"
            )

        receipt_execution_digest = str(
            receipt.get(
                "execution_digest",
                "",
            )
        ).strip()

        if (
            receipt_execution_digest
            and receipt_execution_digest
            != self.execution_digest
        ):
            raise BlotProjectionSessionError(
                "projection artifact execution digest mismatch"
            )

        receipt_profile = str(
            receipt.get(
                "profile",
                receipt.get(
                    "profile_id",
                    "",
                ),
            )
        ).strip()

        if (
            receipt_profile
            and receipt_profile
            != profile_id
        ):
            raise BlotProjectionSessionError(
                "projection artifact profile mismatch"
            )

        existing = self._artifacts.get(
            profile_id
        )

        if existing is not None:
            if (
                existing.normalized()[
                    "digest"
                ]
                != data[
                    "digest"
                ]
            ):
                raise BlotProjectionSessionError(
                    "projection profile artifact conflict"
                )

            return existing

        self._artifacts[
            profile_id
        ] = artifact

        return artifact

    def artifact(
        self,
        profile_id: str,
    ) -> ProjectionArtifact:
        profile_id = _text(
            profile_id,
            "profile_id",
        )

        try:
            return self._artifacts[
                profile_id
            ]
        except KeyError as exc:
            raise BlotProjectionSessionError(
                f"unknown projection artifact: {profile_id}"
            ) from exc

    def artifacts(
        self,
    ) -> tuple[ProjectionArtifact, ...]:
        return tuple(
            self._artifacts[key]
            for key in sorted(
                self._artifacts
            )
        )

    def result(
        self,
        profile_id: str,
    ) -> FinalizationResult:
        profile_id = _text(
            profile_id,
            "profile_id",
        )

        try:
            return self._results[
                profile_id
            ]
        except KeyError as exc:
            raise BlotProjectionSessionError(
                f"profile has not been finalized: {profile_id}"
            ) from exc

    def results(
        self,
    ) -> tuple[FinalizationResult, ...]:
        return tuple(
            self._results[key]
            for key in sorted(
                self._results
            )
        )

    def finalize_profile(
        self,
        profile_id: str,
    ) -> FinalizationResult:
        profile_id = _text(
            profile_id,
            "profile_id",
        )

        self.profiles.get(
            profile_id
        )

        existing = self._results.get(
            profile_id
        )

        if existing is not None:
            return existing

        artifact = self.artifact(
            profile_id
        )

        artifact_data = (
            artifact.normalized()
        )

        lineage = _unique(
            (
                *artifact.lineage,
                self.construction_digest,
                self.execution_digest,
            )
        )

        provenance = _unique(
            (
                *self.provenance,
                *artifact.provenance,
                artifact_data[
                    "digest"
                ],
            )
        )

        request = FinalizationRequest(
            svg=
                artifact.svg,

            document=
                artifact.document,

            execution_contract=
                self.execution_contract,

            projection_receipt=
                artifact.projection_receipt,

            profile_id=
                profile_id,

            expected=
                artifact.expected,

            dependency_digests=
                artifact.dependency_digests,

            lineage=
                lineage,

            provenance=
                provenance,

            projection_id=
                artifact.projection_id,
        )

        result = self.finalizer.finalize(
            request
        )

        result_data = result.normalized()

        verification = result_data[
            "verification"
        ]

        if (
            verification[
                "source_digest"
            ]
            != self.source_digest
        ):
            raise BlotProjectionSessionError(
                "finalization source digest drift"
            )

        if (
            verification[
                "construction_digest"
            ]
            != self.construction_digest
        ):
            raise BlotProjectionSessionError(
                "finalization construction digest drift"
            )

        if (
            verification[
                "execution_digest"
            ]
            != self.execution_digest
        ):
            raise BlotProjectionSessionError(
                "finalization execution digest drift"
            )

        self._results[
            profile_id
        ] = result

        return result

    def finalize_available(
        self,
    ) -> tuple[FinalizationResult, ...]:
        for profile_id in sorted(
            self._artifacts
        ):
            self.finalize_profile(
                profile_id
            )

        return self.results()

    def projection_set(
        self,
    ) -> ProjectionSet | None:
        finalized = [
            result
            for result in self.results()
            if result.normalized()[
                "finalized"
            ]
        ]

        if not finalized:
            return None

        builder = ProjectionSetBuilder(
            source_digest=
                self.source_digest,

            construction_digest=
                self.construction_digest,

            execution_digest=
                self.execution_digest,
        )

        for result in finalized:
            result_data = (
                result.normalized()
            )

            entry = result_data.get(
                "projection_entry"
            )

            if not isinstance(
                entry,
                Mapping,
            ):
                raise BlotProjectionSessionError(
                    "finalized projection is missing registry entry"
                )

            builder.add_entry(
                entry
            )

        return builder.build()

    def terminal(
        self,
    ) -> ProjectionSessionResult:
        if not self._artifacts:
            raise BlotProjectionSessionError(
                "projection session contains no artifacts"
            )

        self.finalize_available()

        requested_profiles = tuple(
            sorted(
                self._artifacts
            )
        )

        finalized_profiles: list[str] = []
        rejected_profiles: list[str] = []
        result_digests: list[str] = []

        ordered_results: list[
            FinalizationResult
        ] = []

        for profile_id in requested_profiles:
            result = self._results[
                profile_id
            ]

            data = result.normalized()

            ordered_results.append(
                result
            )

            result_digests.append(
                data[
                    "digest"
                ]
            )

            if data[
                "finalized"
            ]:
                finalized_profiles.append(
                    profile_id
                )
            else:
                rejected_profiles.append(
                    profile_id
                )

        projection_set = (
            self.projection_set()
        )

        projection_set_digest = (
            None
            if projection_set is None
            else projection_set.normalized()[
                "digest"
            ]
        )

        complete = (
            set(
                canonical_profiles
            )
            <= set(
                finalized_profiles
            )
        )

        if complete:
            if projection_set is None:
                raise BlotProjectionSessionError(
                    "complete session has no projection set"
                )

            if not projection_set.normalized()[
                "complete"
            ]:
                raise BlotProjectionSessionError(
                    "session and projection set completeness disagree"
                )

        receipt = ProjectionSessionReceipt(
            source_digest=
                self.source_digest,

            construction_digest=
                self.construction_digest,

            execution_digest=
                self.execution_digest,

            requested_profiles=
                requested_profiles,

            finalized_profiles=
                tuple(
                    finalized_profiles
                ),

            rejected_profiles=
                tuple(
                    rejected_profiles
                ),

            projection_set_digest=
                projection_set_digest,

            complete=
                complete,

            result_digests=
                tuple(
                    result_digests
                ),

            provenance=
                self.provenance,
        )

        result = ProjectionSessionResult(
            receipt=
                receipt,

            projection_set=
                projection_set,

            results=
                tuple(
                    ordered_results
                ),
        )

        result.normalized()

        return result

    def manifest(
        self,
    ) -> dict[str, Any]:
        artifacts = [
            artifact.normalized()
            for artifact in self.artifacts()
        ]

        results = [
            result.normalized()
            for result in self.results()
        ]

        profiles = (
            self.profiles.manifest()
        )

        registry = (
            self.registry.manifest()
        )

        body = {
            "schema":
                schema,

            "name":
                name,

            "source_digest":
                self.source_digest,

            "construction_digest":
                self.construction_digest,

            "execution_digest":
                self.execution_digest,

            "artifact_count":
                len(artifacts),

            "result_count":
                len(results),

            "artifacts":
                artifacts,

            "results":
                results,

            "profile_registry_digest":
                profiles[
                    "digest"
                ],

            "projection_registry_digest":
                registry[
                    "digest"
                ],

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,

            "construction_owner":
                construction_owner,

            "orchestration_owner":
                orchestration_owner,

            "projection_owner":
                projection_owner,

            "canonical_source":
                "construction-graph",

            "projection_is_authority":
                False,

            "session_is_authority":
                False,

            "creates_authority":
                False,

            "instance_first":
                True,

            "deterministic_projection":
                True,

            "shared_construction":
                True,

            "profile_specific_projection":
                True,

            "hard_gate":
                "execution-ready-no-blocking-ambiguities",
        }

        return {
            **body,
            "digest":
                _digest(body),
        }


def projection_session(
    *,
    source_digest: str,
    construction_digest: str,
    execution_contract: Mapping[str, Any],
    profiles: ProjectionProfileRegistry | None = None,
    registry: ProjectionRegistry | None = None,
    failure_router: Callable[[str], str] | None = None,
    provenance: Iterable[str] = (),
) -> ProjectionSession:
    return ProjectionSession(
        source_digest=
            source_digest,

        construction_digest=
            construction_digest,

        execution_contract=
            execution_contract,

        profiles=
            profiles,

        registry=
            registry,

        failure_router=
            failure_router,

        provenance=
            provenance,
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

        "construction_owner":
            construction_owner,

        "orchestration_owner":
            orchestration_owner,

        "projection_owner":
            projection_owner,

        "input":
            "execution-ready-construction",

        "profile_model":
            "shared-construction-derived-projections",

        "canonical_profiles":
            list(
                canonical_profiles
            ),

        "finalization": [
            "verify",
            "accept",
            "bind-replay",
            "replay",
            "lock",
            "register",
        ],

        "terminal_projection":
            "projection-set",

        "canonical_source":
            "construction-graph",

        "projection_is_authority":
            False,

        "session_is_authority":
            False,

        "creates_authority":
            False,

        "mutates_construction":
            False,

        "provider_execution_owned":
            False,

        "provider_routing_owned":
            False,

        "provider_retry_owned":
            False,

        "provider_fallback_owned":
            False,
    }

    return {
        **body,
        "digest":
            _digest(body),
    }


__all__ = [
    "BlotProjectionSessionError",
    "ProjectionArtifact",
    "ProjectionSession",
    "ProjectionSessionReceipt",
    "ProjectionSessionResult",
    "authority_effect",
    "construction_owner",
    "manifest",
    "max_projection_artifacts",
    "mutation_effect",
    "name",
    "orchestration_owner",
    "projection_only",
    "projection_owner",
    "projection_session",
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
