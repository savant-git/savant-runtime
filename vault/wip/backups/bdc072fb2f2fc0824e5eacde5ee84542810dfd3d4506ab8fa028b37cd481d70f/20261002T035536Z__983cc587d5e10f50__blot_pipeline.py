#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from runtime.translucent.blot_opus import (
    Counterfactual,
    CounterfactualSelector,
    OrchestrationSession,
    ProviderCapability,
    ProviderRegistry,
    SelectionPolicy,
)
from runtime.translucent.blot_reconstruction import (
    Ambiguity,
    Candidate,
    ConstructionPrimitive,
    Evidence,
    ExecutionContract,
    ExecutionStep,
    ReconstructionPipeline,
)
from runtime.translucent.svg.blot_reconstruction import (
    ProjectionBuilder,
    SvgClipPath,
    SvgDocument,
    SvgLinearGradient,
    SvgMask,
    SvgPath,
    SvgRadialGradient,
    SvgStop,
    path_from_primitive,
)


name = "blot."
schema = "savant.translucent.blot.pipeline.v1"
authority_effect = "none"
projection_only = True

max_candidates = 16
max_projections = 16


class BlotPipelineError(ValueError):
    pass


def _canonical(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        _canonical(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def _text(
    value: Any,
    label: str,
) -> str:
    result = str(
        value
    ).strip()

    if not result:
        raise BlotPipelineError(
            f"{label} is required"
        )

    return result


def _unique(
    values: Iterable[Any],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(
                value
            ).strip()
            for value in values
            if str(
                value
            ).strip()
        )
    )


@dataclass(frozen=True, slots=True)
class ProjectionProfile:
    profile_id: str
    width: float
    height: float
    mode: str = "presentation"
    detail: str = "full"
    color: str = "full"
    effects: bool = True

    def normalized(
        self,
    ) -> dict[str, Any]:
        profile_id = _text(
            self.profile_id,
            "profile_id",
        )

        mode = _text(
            self.mode,
            "mode",
        )

        detail = _text(
            self.detail,
            "detail",
        )

        color = _text(
            self.color,
            "color",
        )

        width = float(
            self.width
        )

        height = float(
            self.height
        )

        if (
            width <= 0
            or height <= 0
        ):
            raise BlotPipelineError(
                "projection dimensions must be positive"
            )

        return {
            "profile_id":
                profile_id,

            "width":
                width,

            "height":
                height,

            "mode":
                mode,

            "detail":
                detail,

            "color":
                color,

            "effects":
                bool(
                    self.effects
                ),
        }


@dataclass(frozen=True, slots=True)
class ReconstructionRequest:
    source_digest: str
    preferred_providers: tuple[str, ...] = ()
    projection_profiles: tuple[
        ProjectionProfile,
        ...
    ] = ()
    metadata: Mapping[str, Any] | None = None

    def normalized(
        self,
    ) -> dict[str, Any]:
        profiles = (
            self.projection_profiles
            if self.projection_profiles
            else default_projection_profiles()
        )

        if len(
            profiles
        ) > max_projections:
            raise BlotPipelineError(
                "projection profile limit exceeded"
            )

        profile_data = [
            profile.normalized()
            for profile in profiles
        ]

        profile_ids = [
            profile[
                "profile_id"
            ]
            for profile in profile_data
        ]

        if len(
            set(
                profile_ids
            )
        ) != len(
            profile_ids
        ):
            raise BlotPipelineError(
                "duplicate projection profile id"
            )

        return {
            "schema":
                f"{schema}.request",

            "source_digest":
                _text(
                    self.source_digest,
                    "source_digest",
                ),

            "preferred_providers":
                list(
                    _unique(
                        self.preferred_providers
                    )
                ),

            "projection_profiles":
                profile_data,

            "metadata":
                dict(
                    self.metadata
                    or {}
                ),

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }


@dataclass(frozen=True, slots=True)
class ReconstructionReceipt:
    request_digest: str
    construction_digest: str
    dry_run_digest: str
    contract_digest: str
    selected_candidate: str
    projection_digests: Mapping[str, str]
    replay_digest: str | None = None

    def normalized(
        self,
    ) -> dict[str, Any]:
        result = {
            "schema":
                f"{schema}.receipt",

            "request_digest":
                _text(
                    self.request_digest,
                    "request_digest",
                ),

            "construction_digest":
                _text(
                    self.construction_digest,
                    "construction_digest",
                ),

            "dry_run_digest":
                _text(
                    self.dry_run_digest,
                    "dry_run_digest",
                ),

            "contract_digest":
                _text(
                    self.contract_digest,
                    "contract_digest",
                ),

            "selected_candidate":
                _text(
                    self.selected_candidate,
                    "selected_candidate",
                ),

            "projection_digests":
                {
                    str(
                        key
                    ):
                        str(
                            value
                        )
                    for key, value
                    in sorted(
                        self.projection_digests.items()
                    )
                },

            "replay_digest":
                self.replay_digest,

            "authority_effect":
                "none",

            "projection_only":
                True,
        }

        result[
            "digest"
        ] = _digest(
            result
        )

        return result


def default_projection_profiles(
) -> tuple[ProjectionProfile, ...]:
    return (
        ProjectionProfile(
            profile_id="presentation",
            width=1024,
            height=1024,
            mode="presentation",
            detail="full",
            color="full",
            effects=True,
        ),
        ProjectionProfile(
            profile_id="standard",
            width=512,
            height=512,
            mode="standard",
            detail="standard",
            color="full",
            effects=True,
        ),
        ProjectionProfile(
            profile_id="flat",
            width=512,
            height=512,
            mode="flat",
            detail="standard",
            color="full",
            effects=False,
        ),
        ProjectionProfile(
            profile_id="monochrome",
            width=512,
            height=512,
            mode="monochrome",
            detail="standard",
            color="monochrome",
            effects=False,
        ),
        ProjectionProfile(
            profile_id="micro",
            width=64,
            height=64,
            mode="micro",
            detail="micro",
            color="full",
            effects=False,
        ),
    )


class BlotPipeline:
    def __init__(
        self,
        request: ReconstructionRequest,
        *,
        providers: Iterable[
            ProviderCapability
        ] = (),
        selection_policy: SelectionPolicy | None = None,
    ) -> None:
        self.request = request

        request_data = request.normalized()

        self.request_data = request_data

        self.request_digest = _digest(
            request_data
        )

        self.reconstruction = ReconstructionPipeline(
            source_digest=request_data[
                "source_digest"
            ],
            preferred_providers=tuple(
                request_data[
                    "preferred_providers"
                ]
            ),
        )

        self.provider_registry = ProviderRegistry(
            providers
        )

        self.opus = OrchestrationSession(
            self.reconstruction,
            provider_registry=self.provider_registry,
        )

        self.selector = CounterfactualSelector(
            selection_policy
        )

        self._selected_candidate: str | None = None
        self._contract: ExecutionContract | None = None

        self._documents: dict[
            str,
            SvgDocument,
        ] = {}

        self._projection_receipts: dict[
            str,
            dict[str, Any],
        ] = {}

    def add_evidence(
        self,
        evidence: Evidence,
    ) -> str:
        return self.reconstruction.add_evidence(
            evidence
        )

    def add_ambiguity(
        self,
        ambiguity: Ambiguity,
    ) -> str:
        return self.reconstruction.add_ambiguity(
            ambiguity
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

    def rung_packet(
        self,
        rung: int,
    ) -> dict[str, Any]:
        return self.reconstruction.opus_packet(
            rung
        )

    def construction_graph(
        self,
    ) -> dict[str, Any]:
        return self.reconstruction.construction_graph()

    def dry_run(
        self,
    ) -> dict[str, Any]:
        return self.reconstruction.dry_run()

    def select_counterfactual(
        self,
        candidates: Sequence[
            Counterfactual
        ],
    ) -> Counterfactual:
        winner = self.selector.select(
            candidates
        )

        self._selected_candidate = (
            winner.candidate_id
        )

        return winner

    def compile(
        self,
        steps: Sequence[
            ExecutionStep
        ],
        *,
        candidate_id: str | None = None,
    ) -> ExecutionContract:
        selected = (
            candidate_id
            if candidate_id is not None
            else self._selected_candidate
        )

        if selected is None:
            raise BlotPipelineError(
                "candidate must be selected before compilation"
            )

        contract = (
            self.reconstruction
            .compile_execution_contract(
                selected,
                steps,
            )
        )

        normalized = contract.normalized()

        if not normalized[
            "execution_ready"
        ]:
            raise BlotPipelineError(
                "execution contract is blocked"
            )

        self._selected_candidate = selected
        self._contract = contract

        return contract

    def execution_packet(
        self,
    ) -> dict[str, Any]:
        if self._contract is None:
            raise BlotPipelineError(
                "execution contract has not been compiled"
            )

        return self.opus.execution_packet(
            self._contract
        )

    def projection_builder(
        self,
        profile: ProjectionProfile,
    ) -> ProjectionBuilder:
        if self._contract is None:
            raise BlotPipelineError(
                "execution contract has not been compiled"
            )

        profile_data = profile.normalized()

        return ProjectionBuilder(
            self._contract,
            width=profile_data[
                "width"
            ],
            height=profile_data[
                "height"
            ],
        )

    def project(
        self,
        profile: ProjectionProfile,
        *,
        paths: Sequence[
            tuple[
                str,
                SvgPath,
                Sequence[str],
                str | None,
            ]
        ] = (),
        gradients: Sequence[
            SvgLinearGradient
            | SvgRadialGradient
        ] = (),
        clips: Sequence[
            SvgClipPath
        ] = (),
        masks: Sequence[
            SvgMask
        ] = (),
    ) -> SvgDocument:
        profile_data = profile.normalized()

        profile_id = profile_data[
            "profile_id"
        ]

        builder = self.projection_builder(
            profile
        )

        for gradient in gradients:
            builder.add_gradient(
                gradient
            )

        for clip in clips:
            builder.add_clip(
                clip
            )

        for mask in masks:
            builder.add_mask(
                mask
            )

        for (
            layer,
            path,
            primitive_ids,
            step_id,
        ) in paths:
            builder.add(
                layer,
                path,
                primitive_ids=primitive_ids,
                step_id=step_id,
            )

        document = builder.document()

        self._documents[
            profile_id
        ] = document

        self._projection_receipts[
            profile_id
        ] = builder.projection_receipt()

        return document

    def project_primitive_graph(
        self,
        profile: ProjectionProfile,
        *,
        layer: str = "geometry",
        fill: str | None = None,
        stroke: str | None = None,
        stroke_width: float | None = None,
    ) -> SvgDocument:
        graph = self.construction_graph()

        paths: list[
            tuple[
                str,
                SvgPath,
                Sequence[str],
                str | None,
            ]
        ] = []

        for primitive in graph[
            "primitives"
        ]:
            parameters = primitive.get(
                "parameters",
                {},
            )

            if not isinstance(
                parameters,
                Mapping,
            ):
                continue

            if (
                "d" not in parameters
                and "path" not in parameters
            ):
                continue

            primitive_id = primitive[
                "primitive_id"
            ]

            path = path_from_primitive(
                primitive,
                fill=fill,
                stroke=stroke,
                stroke_width=stroke_width,
            )

            paths.append(
                (
                    layer,
                    path,
                    (
                        primitive_id,
                    ),
                    None,
                )
            )

        return self.project(
            profile,
            paths=paths,
        )

    def document(
        self,
        profile_id: str,
    ) -> SvgDocument:
        profile_id = _text(
            profile_id,
            "profile_id",
        )

        document = self._documents.get(
            profile_id
        )

        if document is None:
            raise BlotPipelineError(
                "projection has not been generated: "
                f"{profile_id}"
            )

        return document

    def svg(
        self,
        profile_id: str,
    ) -> str:
        return self.document(
            profile_id
        ).render()

    def projection_receipt(
        self,
        profile_id: str,
    ) -> Mapping[str, Any]:
        profile_id = _text(
            profile_id,
            "profile_id",
        )

        receipt = self._projection_receipts.get(
            profile_id
        )

        if receipt is None:
            raise BlotPipelineError(
                "projection receipt does not exist: "
                f"{profile_id}"
            )

        return dict(
            receipt
        )

    def receipt(
        self,
    ) -> ReconstructionReceipt:
        if self._contract is None:
            raise BlotPipelineError(
                "execution contract has not been compiled"
            )

        if self._selected_candidate is None:
            raise BlotPipelineError(
                "candidate has not been selected"
            )

        if not self._projection_receipts:
            raise BlotPipelineError(
                "no projections have been generated"
            )

        graph = self.construction_graph()
        dry_run = self.dry_run()
        contract = self._contract.normalized()

        replay = self.opus.replay_manifest()

        return ReconstructionReceipt(
            request_digest=self.request_digest,
            construction_digest=graph[
                "digest"
            ],
            dry_run_digest=dry_run[
                "digest"
            ],
            contract_digest=contract[
                "digest"
            ],
            selected_candidate=(
                self._selected_candidate
            ),
            projection_digests={
                profile_id:
                    receipt[
                        "svg_digest"
                    ]
                for profile_id, receipt
                in sorted(
                    self._projection_receipts.items()
                )
            },
            replay_digest=replay[
                "digest"
            ],
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        reconstruction_manifest = (
            self.reconstruction.manifest()
        )

        result = {
            "schema":
                f"{schema}.manifest",

            "name":
                name,

            "request":
                self.request_data,

            "request_digest":
                self.request_digest,

            "reconstruction":
                reconstruction_manifest,

            "orchestration":
                {
                    "owner":
                        "opus",

                    "provider_neutral":
                        True,

                    "bounded_parallelism":
                        True,

                    "bounded_candidates":
                        True,

                    "failure_receipts":
                        True,

                    "typed_segues":
                        True,

                    "replay":
                        True,
                },

            "construction":
                {
                    "owner":
                        "blot.",

                    "substantiate_once":
                        True,

                    "instances_over_copies":
                        True,

                    "semantic_geometry":
                        True,

                    "explicit_ambiguity":
                        True,

                    "geometry_owns_shape":
                        True,

                    "materials_decorate_geometry":
                        True,
                },

            "projection":
                {
                    "svg_is_derived":
                        True,

                    "canonical_serialization":
                        True,

                    "stable_hashing":
                        True,

                    "lineage":
                        True,

                    "provenance":
                        True,

                    "optical_profiles":
                        [
                            profile.normalized()
                            for profile
                            in default_projection_profiles()
                        ],
                },

            "authority_effect":
                "none",

            "projection_only":
                True,
        }

        result[
            "digest"
        ] = _digest(
            result
        )

        return result


def selftest(
) -> dict[str, Any]:
    request = ReconstructionRequest(
        source_digest="blot-pipeline-source",
        preferred_providers=(
            "local",
        ),
    )

    pipeline = BlotPipeline(
        request,
        providers=(
            ProviderCapability(
                provider_id="local",
                capabilities=(
                    "*",
                ),
                deterministic=True,
                local=True,
                priority=1,
            ),
        ),
    )

    evidence_id = pipeline.add_evidence(
        Evidence(
            evidence_id="silhouette",
            kind="silhouette",
            payload={
                "region":
                    "primary",
            },
            confidence=1.0,
            provenance=(
                "selftest",
            ),
        )
    )

    primitive_id = pipeline.substantiate(
        ConstructionPrimitive(
            primitive_id="primary-ribbon",
            kind="cubic-bezier-shape",
            parameters={
                "d":
                    "M 10 50 "
                    "C 20 10 80 10 90 50 "
                    "C 80 90 20 90 10 50 Z",

                "fill":
                    "#202020",

                "fill_rule":
                    "nonzero",
            },
            evidence_ids=(
                evidence_id,
            ),
            confidence=1.0,
            provenance=(
                "selftest",
            ),
        )
    )

    candidate_id = pipeline.add_candidate(
        Candidate(
            candidate_id="semantic-bezier",
            strategy="semantic-bezier",
            primitive_ids=(
                primitive_id,
            ),
            predicted_cost={
                "paths":
                    1,

                "anchors":
                    4,
            },
            predicted_quality={
                "fidelity":
                    1.0,

                "structural":
                    1.0,

                "editability":
                    1.0,

                "economy":
                    1.0,

                "compatibility":
                    1.0,
            },
        )
    )

    counterfactual = Counterfactual(
        candidate_id=candidate_id,
        construction_digest=(
            pipeline
            .construction_graph()[
                "digest"
            ]
        ),
        method="semantic-bezier",
        predicted_quality={
            "fidelity":
                1.0,

            "structural":
                1.0,

            "editability":
                1.0,

            "economy":
                1.0,

            "compatibility":
                1.0,
        },
        predicted_cost={
            "paths":
                0.01,

            "anchors":
                0.04,
        },
    )

    selected = pipeline.select_counterfactual(
        (
            counterfactual,
        )
    )

    contract = pipeline.compile(
        (
            ExecutionStep(
                step_id="build-primary-ribbon",
                stage_id="bezier-build",
                operation="construct-cubic-bezier",
                primitive_ids=(
                    primitive_id,
                ),
            ),
        ),
        candidate_id=selected.candidate_id,
    )

    graph = pipeline.construction_graph()

    primitive = graph[
        "primitives"
    ][0]

    gradient = SvgLinearGradient(
        gradient_id="primary-material",
        x1=0,
        y1=0,
        x2=1,
        y2=1,
        stops=(
            SvgStop(
                0.0,
                "#101010",
            ),
            SvgStop(
                0.45,
                "#f0f0f0",
            ),
            SvgStop(
                1.0,
                "#202020",
            ),
        ),
    )

    path = path_from_primitive(
        primitive,
        fill="url(#primary-material)",
    )

    profile = ProjectionProfile(
        profile_id="presentation",
        width=100,
        height=100,
    )

    document = pipeline.project(
        profile,
        gradients=(
            gradient,
        ),
        paths=(
            (
                "geometry",
                path,
                (
                    primitive_id,
                ),
                "build-primary-ribbon",
            ),
        ),
    )

    svg_a = document.render()
    svg_b = pipeline.svg(
        "presentation"
    )

    receipt_a = pipeline.receipt().normalized()
    receipt_b = pipeline.receipt().normalized()

    manifest_a = pipeline.manifest()
    manifest_b = pipeline.manifest()

    contract_data = contract.normalized()

    checks = {
        "name_exact":
            name
            == "blot.",

        "authority_none":
            authority_effect
            == "none",

        "projection_only":
            projection_only
            is True,

        "candidate_selected":
            selected.candidate_id
            == "semantic-bezier",

        "contract_ready":
            contract_data[
                "execution_ready"
            ]
            is True,

        "opus_packet":
            pipeline.execution_packet()[
                "owner"
            ]
            == "opus",

        "svg_generated":
            "<svg "
            in svg_a,

        "semantic_path":
            "primitive-primary-ribbon"
            in svg_a,

        "gradient_generated":
            "primary-material"
            in svg_a,

        "deterministic_svg":
            svg_a
            == svg_b,

        "deterministic_receipt":
            receipt_a
            == receipt_b,

        "deterministic_manifest":
            manifest_a
            == manifest_b,

        "projection_recorded":
            "presentation"
            in receipt_a[
                "projection_digests"
            ],

        "construction_lineage":
            receipt_a[
                "construction_digest"
            ]
            == pipeline.construction_graph()[
                "digest"
            ],
    }

    return {
        "schema":
            f"{schema}.selftest",

        "ok":
            all(
                checks.values()
            ),

        "checks":
            checks,

        "request_digest":
            pipeline.request_digest,

        "manifest_digest":
            manifest_a[
                "digest"
            ],

        "receipt_digest":
            receipt_a[
                "digest"
            ],

        "svg_digest":
            document.digest(),
    }


__all__ = [
    "BlotPipeline",
    "BlotPipelineError",
    "ProjectionProfile",
    "ReconstructionReceipt",
    "ReconstructionRequest",
    "authority_effect",
    "default_projection_profiles",
    "max_candidates",
    "max_projections",
    "name",
    "projection_only",
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
