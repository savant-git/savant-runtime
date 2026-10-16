#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from runtime.opus_ai_adapter import OpusAIAdapter
from runtime.translucent.blot_opus import (
    Counterfactual,
    CounterfactualSelector,
    OrchestrationSession,
    SelectionPolicy,
    TypedSegue,
)
from runtime.translucent.blot_reconstruction import (
    Candidate,
    ConstructionPrimitive,
    Evidence,
    ExecutionContract,
    ExecutionStep,
    ReconstructionPipeline,
)


name = "blot."
schema = "savant.translucent.blot.pipeline.v2"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

construction_owner = "blot."
orchestration_owner = "opus"
projection_owner = "blot."

max_projection_profiles = 16


class BlotPipelineError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = _canonical(value).encode(
            "utf-8"
        )

    return hashlib.sha256(
        raw
    ).hexdigest()


def _text(
    value: Any,
    field_name: str,
) -> str:
    result = str(
        value or ""
    ).strip()

    if not result:
        raise BlotPipelineError(
            f"{field_name} is required"
        )

    return result


def _unique(
    values: Iterable[Any],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(value).strip()
            for value in values
            if str(value).strip()
        )
    )


@dataclass(frozen=True, slots=True)
class ReconstructionRequest:
    source_digest: str
    source_kind: str = "raster"
    objective: str = (
        "recover the smallest semantically correct "
        "editable vector construction that reproduces "
        "the recoverable visual information"
    )
    constraints: Mapping[str, Any] = field(
        default_factory=dict
    )
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.request",

            "source_digest":
                _text(
                    self.source_digest,
                    "source_digest",
                ),

            "source_kind":
                _text(
                    self.source_kind,
                    "source_kind",
                ),

            "objective":
                _text(
                    self.objective,
                    "objective",
                ),

            "constraints":
                dict(
                    self.constraints
                ),

            "provenance":
                list(
                    _unique(
                        self.provenance
                    )
                ),

            "authority_effect":
                "none",

            "mutation_effect":
                "none",

            "projection_only":
                True,
        }

        body[
            "request_id"
        ] = (
            "blot-request-"
            + _digest(
                body
            )[:24]
        )

        body[
            "digest"
        ] = _digest(
            body
        )

        return body


@dataclass(frozen=True, slots=True)
class ProjectionProfile:
    profile_id: str
    purpose: str
    material_detail: str
    lighting_detail: str
    effects: str
    geometry_policy: str
    optical_policy: str
    constraints: Mapping[str, Any] = field(
        default_factory=dict
    )

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.projection-profile",

            "profile_id":
                _text(
                    self.profile_id,
                    "profile_id",
                ),

            "purpose":
                _text(
                    self.purpose,
                    "purpose",
                ),

            "material_detail":
                _text(
                    self.material_detail,
                    "material_detail",
                ),

            "lighting_detail":
                _text(
                    self.lighting_detail,
                    "lighting_detail",
                ),

            "effects":
                _text(
                    self.effects,
                    "effects",
                ),

            "geometry_policy":
                _text(
                    self.geometry_policy,
                    "geometry_policy",
                ),

            "optical_policy":
                _text(
                    self.optical_policy,
                    "optical_policy",
                ),

            "constraints":
                dict(
                    self.constraints
                ),

            "authority_effect":
                "none",
        }

        body[
            "digest"
        ] = _digest(
            body
        )

        return body


def default_projection_profiles(
) -> tuple[
    ProjectionProfile,
    ...
]:
    return (
        ProjectionProfile(
            profile_id="presentation",
            purpose=(
                "canonical high-fidelity "
                "presentation projection"
            ),
            material_detail="full",
            lighting_detail="full",
            effects="restrained-full",
            geometry_policy=(
                "canonical-semantic-geometry"
            ),
            optical_policy=(
                "presentation-scale"
            ),
            constraints={
                "preserve_materials": True,
                "preserve_depth": True,
                "preserve_masks": True,
                "preserve_clips": True,
            },
        ),
        ProjectionProfile(
            profile_id="standard",
            purpose=(
                "general-purpose vector "
                "projection"
            ),
            material_detail="balanced",
            lighting_detail="balanced",
            effects="restrained",
            geometry_policy=(
                "canonical-semantic-geometry"
            ),
            optical_policy="standard-scale",
            constraints={
                "preserve_topology": True,
                "preserve_silhouette": True,
            },
        ),
        ProjectionProfile(
            profile_id="flat",
            purpose=(
                "flat simplified vector "
                "projection"
            ),
            material_detail="flat",
            lighting_detail="none",
            effects="none",
            geometry_policy=(
                "canonical-geometry-with-"
                "material-collapse"
            ),
            optical_policy="standard-scale",
            constraints={
                "preserve_topology": True,
                "preserve_negative_space": True,
                "preserve_identity": True,
            },
        ),
        ProjectionProfile(
            profile_id="monochrome",
            purpose=(
                "single-color identity "
                "projection"
            ),
            material_detail="monochrome",
            lighting_detail="none",
            effects="none",
            geometry_policy=(
                "canonical-geometry-with-"
                "single-paint"
            ),
            optical_policy="standard-scale",
            constraints={
                "preserve_topology": True,
                "preserve_negative_space": True,
                "preserve_silhouette": True,
            },
        ),
        ProjectionProfile(
            profile_id="micro",
            purpose=(
                "small optical-size "
                "projection"
            ),
            material_detail="reduced",
            lighting_detail="reduced",
            effects="minimal",
            geometry_policy=(
                "optically-adjusted-derived-"
                "geometry"
            ),
            optical_policy="micro-scale",
            constraints={
                "preserve_identity": True,
                "favor_legibility": True,
                "remove_nonessential_detail":
                    True,
            },
        ),
    )


class BlotPipeline:
    def __init__(
        self,
        request: ReconstructionRequest,
        *,
        opus_adapter: OpusAIAdapter | None = None,
        selection_policy: SelectionPolicy | None = None,
        projection_profiles: Iterable[
            ProjectionProfile
        ] | None = None,
    ) -> None:
        self.request = request

        request_data = (
            request.normalized()
        )

        self.reconstruction = (
            ReconstructionPipeline(
                source_digest=request_data[
                    "source_digest"
                ]
            )
        )

        self.orchestration = (
            OrchestrationSession(
                self.reconstruction,
                opus_adapter=opus_adapter,
            )
        )

        self.selector = (
            CounterfactualSelector(
                selection_policy
            )
        )

        profiles = tuple(
            projection_profiles
            if projection_profiles
            is not None
            else default_projection_profiles()
        )

        if not profiles:
            raise BlotPipelineError(
                "at least one projection "
                "profile is required"
            )

        if (
            len(profiles)
            > max_projection_profiles
        ):
            raise BlotPipelineError(
                "projection profile limit "
                "exceeded"
            )

        self._profiles: dict[
            str,
            ProjectionProfile,
        ] = {}

        for profile in profiles:
            normalized = (
                profile.normalized()
            )

            profile_id = normalized[
                "profile_id"
            ]

            existing = (
                self._profiles.get(
                    profile_id
                )
            )

            if existing is not None:
                if (
                    existing.normalized()
                    != normalized
                ):
                    raise BlotPipelineError(
                        "projection profile "
                        "identity conflict: "
                        f"{profile_id}"
                    )

                continue

            self._profiles[
                profile_id
            ] = profile

        self._selected_candidate_id: (
            str
            | None
        ) = None

        self._execution_contract: (
            ExecutionContract
            | None
        ) = None

    def add_evidence(
        self,
        evidence: Evidence,
    ) -> str:
        return self.reconstruction.add_evidence(
            evidence
        )

    def substantiate(
        self,
        primitive: ConstructionPrimitive,
    ) -> str:
        return self.reconstruction.substantiate(
            primitive
        )

    def add_candidate(
        self,
        candidate: Candidate,
    ) -> str:
        return self.reconstruction.add_candidate(
            candidate
        )

    def ingest_rung(
        self,
        rung: int,
    ) -> tuple[Any, ...]:
        return self.orchestration.ingest_rung(
            rung
        )

    def ready_work(
        self,
    ) -> tuple[Any, ...]:
        return self.orchestration.ready()

    def delegate(
        self,
        work_id: str,
    ) -> dict[str, Any]:
        return self.orchestration.delegate(
            work_id
        )

    def record_result(
        self,
        work_id: str,
        payload: Mapping[str, Any],
        *,
        confidence: float = 1.0,
        provenance: Iterable[str] = (),
    ) -> Any:
        return self.orchestration.record_result(
            work_id,
            payload,
            confidence=confidence,
            provenance=provenance,
        )

    def select_construction(
        self,
        counterfactuals: Iterable[
            Counterfactual
        ],
    ) -> Counterfactual:
        candidates = tuple(
            counterfactuals
        )

        selected = self.selector.select(
            candidates
        )

        self._selected_candidate_id = (
            selected.candidate_id
        )

        return selected

    def compile_execution(
        self,
        candidate_id: str,
        steps: Iterable[
            ExecutionStep
        ],
    ) -> ExecutionContract:
        candidate_id = _text(
            candidate_id,
            "candidate_id",
        )

        if (
            self._selected_candidate_id
            is not None
            and candidate_id
            != self._selected_candidate_id
        ):
            raise BlotPipelineError(
                "execution candidate does not "
                "match selected construction"
            )

        contract = (
            self.reconstruction
            .compile_execution_contract(
                candidate_id,
                tuple(
                    steps
                ),
            )
        )

        contract_data = (
            contract.normalized()
        )

        if not contract_data.get(
            "execution_ready"
        ):
            raise BlotPipelineError(
                "rung 3 cannot start because "
                "the execution contract is "
                "not ready"
            )

        self._selected_candidate_id = (
            candidate_id
        )

        self._execution_contract = (
            contract
        )

        return contract

    def execution_packet(
        self,
    ) -> dict[str, Any]:
        if self._execution_contract is None:
            raise BlotPipelineError(
                "execution contract has not "
                "been compiled"
            )

        return (
            self.orchestration
            .execution_packet(
                self._execution_contract
            )
        )

    def profile(
        self,
        profile_id: str,
    ) -> ProjectionProfile:
        profile_id = _text(
            profile_id,
            "profile_id",
        )

        profile = self._profiles.get(
            profile_id
        )

        if profile is None:
            raise BlotPipelineError(
                "unknown projection profile: "
                f"{profile_id}"
            )

        return profile

    def projection_profiles(
        self,
    ) -> tuple[
        ProjectionProfile,
        ...
    ]:
        return tuple(
            self._profiles[
                profile_id
            ]
            for profile_id
            in self._profiles
        )

    def projection_request(
        self,
        profile_id: str,
        *,
        width: float,
        height: float,
    ) -> dict[str, Any]:
        if self._execution_contract is None:
            raise BlotPipelineError(
                "projection requires a ready "
                "execution contract"
            )

        profile = self.profile(
            profile_id
        )

        contract_data = (
            self._execution_contract
            .normalized()
        )

        if not contract_data.get(
            "execution_ready"
        ):
            raise BlotPipelineError(
                "projection cannot derive from "
                "an unready execution contract"
            )

        try:
            width_value = float(
                width
            )
            height_value = float(
                height
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise BlotPipelineError(
                "projection dimensions must "
                "be numeric"
            ) from exc

        if (
            width_value <= 0
            or height_value <= 0
        ):
            raise BlotPipelineError(
                "projection dimensions must "
                "be positive"
            )

        body = {
            "schema":
                f"{schema}.projection-request",

            "source_request":
                self.request.normalized(),

            "construction":
                self.reconstruction
                .construction_graph(),

            "execution_contract":
                contract_data,

            "profile":
                profile.normalized(),

            "viewport": {
                "width":
                    width_value,

                "height":
                    height_value,
            },

            "projection_owner":
                projection_owner,

            "svg_is_derived":
                True,

            "authority_effect":
                "none",

            "mutation_effect":
                "none",

            "projection_only":
                True,
        }

        body[
            "digest"
        ] = _digest(
            body
        )

        return body

    def bind_projection(
        self,
        profile_id: str,
        projection_digest: str,
    ) -> str:
        if self._execution_contract is None:
            raise BlotPipelineError(
                "projection binding requires "
                "an execution contract"
            )

        profile = self.profile(
            profile_id
        )

        contract_data = (
            self._execution_contract
            .normalized()
        )

        segue = TypedSegue(
            kind="projection-handoff",
            source=contract_data[
                "digest"
            ],
            target=_text(
                projection_digest,
                "projection_digest",
            ),
            contract={
                "profile":
                    profile.normalized(),

                "source_is_authoritative":
                    False,

                "projection_is_authoritative":
                    False,

                "svg_is_derived":
                    True,

                "authority_effect":
                    "none",
            },
            lineage=(
                contract_data[
                    "digest"
                ],
            ),
            provenance=(
                "blot-pipeline",
            ),
        )

        return self.orchestration.add_segue(
            segue
        )

    def replay_manifest(
        self,
    ) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.replay",

            "request":
                self.request.normalized(),

            "construction":
                self.reconstruction.manifest(),

            "orchestration":
                self.orchestration
                .replay_manifest(),

            "projection_profiles":
                [
                    self._profiles[
                        profile_id
                    ].normalized()
                    for profile_id
                    in self._profiles
                ],

            "selected_candidate_id":
                self._selected_candidate_id,

            "execution_contract":
                (
                    self._execution_contract
                    .normalized()
                    if self._execution_contract
                    is not None
                    else None
                ),

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,
        }

        body[
            "digest"
        ] = _digest(
            body
        )

        return body

    def manifest(
        self,
    ) -> dict[str, Any]:
        body = {
            "schema":
                schema,

            "name":
                name,

            "request":
                self.request.normalized(),

            "construction": {
                "owner":
                    construction_owner,

                "representation":
                    "construction-graph",

                "instance_first":
                    True,

                "semantic_primitives":
                    True,

                "typed_relationships":
                    True,

                "geometry_owns_shape":
                    True,

                "materials_decorate":
                    True,

                "authority_effect":
                    "none",
            },

            "orchestration": {
                "owner":
                    orchestration_owner,

                "provider_routing":
                    "opus",

                "provider_execution":
                    "opus",

                "provider_selection":
                    "runtime.opus_ai_adapter",

                "blot_owns_provider_policy":
                    False,

                "blot_owns_retry_policy":
                    False,

                "blot_owns_fallback_policy":
                    False,

                "blot_owns_cost_policy":
                    False,

                "blot_owns_latency_policy":
                    False,
            },

            "projection": {
                "owner":
                    projection_owner,

                "svg_is_derived":
                    True,

                "projection_is_authority":
                    False,

                "canonical_source":
                    "construction-graph",

                "profiles":
                    list(
                        self._profiles
                    ),
            },

            "rungs": {
                "understand":
                    32,

                "prove":
                    28,

                "construct":
                    32,

                "total":
                    92,
            },

            "verification_lock": {
                "sequence": [
                    "render",
                    "measure",
                    "compare",
                    "accept-or-reject",
                ],

                "failure_routing":
                    "earliest-causal-stage",
            },

            "selected_candidate_id":
                self._selected_candidate_id,

            "execution_ready":
                (
                    self._execution_contract
                    is not None
                    and self._execution_contract
                    .normalized()
                    .get(
                        "execution_ready"
                    )
                    is True
                ),

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,
        }

        body[
            "digest"
        ] = _digest(
            body
        )

        return body


def reconstruction_pipeline(
    source_digest: str,
    *,
    source_kind: str = "raster",
    objective: str | None = None,
    constraints: Mapping[
        str,
        Any
    ] | None = None,
    provenance: Iterable[str] = (),
    opus_adapter: OpusAIAdapter | None = None,
) -> BlotPipeline:
    request = ReconstructionRequest(
        source_digest=source_digest,
        source_kind=source_kind,
        objective=(
            objective
            if objective is not None
            else ReconstructionRequest(
                source_digest=source_digest
            ).objective
        ),
        constraints=dict(
            constraints
            or {}
        ),
        provenance=tuple(
            provenance
        ),
    )

    return BlotPipeline(
        request,
        opus_adapter=opus_adapter,
    )


def selftest() -> dict[str, Any]:
    request = ReconstructionRequest(
        source_digest=(
            "verification-source"
        ),
        provenance=(
            "selftest",
        ),
    )

    pipeline_a = BlotPipeline(
        request
    )

    pipeline_b = BlotPipeline(
        request
    )

    manifest_a = (
        pipeline_a.manifest()
    )

    manifest_b = (
        pipeline_b.manifest()
    )

    replay_a = (
        pipeline_a.replay_manifest()
    )

    replay_b = (
        pipeline_b.replay_manifest()
    )

    profiles = (
        pipeline_a
        .projection_profiles()
    )

    profile_ids = [
        profile.profile_id
        for profile in profiles
    ]

    candidate_a = Counterfactual(
        candidate_id="semantic",
        construction_digest=(
            "semantic-construction"
        ),
        method=(
            "semantic-bezier"
        ),
        predicted_quality={
            "fidelity": 0.96,
            "structural": 1.0,
            "editability": 1.0,
            "economy": 1.0,
            "compatibility": 1.0,
        },
        predicted_cost={
            "paths": 3,
            "anchors": 18,
        },
    )

    candidate_b = Counterfactual(
        candidate_id="dense",
        construction_digest=(
            "dense-construction"
        ),
        method=(
            "dense-contour"
        ),
        predicted_quality={
            "fidelity": 0.97,
            "structural": 0.3,
            "editability": 0.2,
            "economy": 0.1,
            "compatibility": 0.8,
        },
        predicted_cost={
            "paths": 40,
            "anchors": 5000,
        },
    )

    selected_a = (
        pipeline_a
        .select_construction(
            (
                candidate_a,
                candidate_b,
            )
        )
    )

    selected_b = (
        pipeline_b
        .select_construction(
            (
                candidate_a,
                candidate_b,
            )
        )
    )

    checks = {
        "name_exact":
            name
            == "blot.",

        "authority_none":
            authority_effect
            == "none",

        "mutation_none":
            mutation_effect
            == "none",

        "projection_only":
            projection_only
            is True,

        "construction_owner":
            construction_owner
            == "blot.",

        "orchestration_owner":
            orchestration_owner
            == "opus",

        "projection_owner":
            projection_owner
            == "blot.",

        "rung_count":
            (
                manifest_a[
                    "rungs"
                ][
                    "total"
                ]
                == 92
            ),

        "projection_profiles":
            profile_ids
            == [
                "presentation",
                "standard",
                "flat",
                "monochrome",
                "micro",
            ],

        "svg_derived":
            manifest_a[
                "projection"
            ][
                "svg_is_derived"
            ]
            is True,

        "opus_owns_routing":
            manifest_a[
                "orchestration"
            ][
                "provider_routing"
            ]
            == "opus",

        "opus_owns_execution":
            manifest_a[
                "orchestration"
            ][
                "provider_execution"
            ]
            == "opus",

        "blot_does_not_own_provider_policy":
            manifest_a[
                "orchestration"
            ][
                "blot_owns_provider_policy"
            ]
            is False,

        "deterministic_manifest":
            manifest_a
            == manifest_b,

        "deterministic_replay":
            replay_a
            == replay_b,

        "semantic_candidate_selected":
            selected_a.candidate_id
            == "semantic",

        "candidate_selection_deterministic":
            selected_a.normalized()
            == selected_b.normalized(),
    }

    result = {
        "schema":
            f"{schema}.selftest",

        "ok":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "manifest":
            pipeline_a.manifest(),

        "replay_digest":
            pipeline_a
            .replay_manifest()[
                "digest"
            ],

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,
    }

    result[
        "digest"
    ] = _digest(
        result
    )

    return result


__all__ = [
    "BlotPipeline",
    "BlotPipelineError",
    "ProjectionProfile",
    "ReconstructionRequest",
    "authority_effect",
    "construction_owner",
    "default_projection_profiles",
    "max_projection_profiles",
    "mutation_effect",
    "name",
    "orchestration_owner",
    "projection_only",
    "projection_owner",
    "reconstruction_pipeline",
    "schema",
    "selftest",
]


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
)
