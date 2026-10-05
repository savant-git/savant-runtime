#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from runtime.opus_ai_adapter import OpusAIAdapter
from runtime.translucent.blot_pipeline import (
    BlotPipeline,
    BlotPipelineError,
    ProjectionProfile,
    ReconstructionRequest,
    default_projection_profiles,
)
from runtime.translucent.blot_reconstruction import (
    Candidate,
    ConstructionPrimitive,
    ConstructionSegue,
    Evidence,
    ExecutionContract,
    ExecutionStep,
    OpusWorkUnit,
)
from runtime.translucent.svg.blot_reconstruction import (
    BlotSvgError,
    ProjectionBuilder,
    SvgClipPath,
    SvgDocument,
    SvgGroup,
    SvgLinearGradient,
    SvgMask,
    SvgPath,
    SvgRadialGradient,
)


name = "blot."
schema = "savant.translucent.blot.integration.v3"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

construction_owner = "blot."
orchestration_owner = "opus"
projection_owner = "blot."


class BlotIntegrationError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
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
        raise BlotIntegrationError(
            f"{field_name} is required"
        )

    return result


def _finite(
    value: Any,
    field_name: str,
) -> float:
    try:
        result = float(value)
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise BlotIntegrationError(
            f"{field_name} must be numeric"
        ) from exc

    if not math.isfinite(result):
        raise BlotIntegrationError(
            f"{field_name} must be finite"
        )

    return result


def _positive(
    value: Any,
    field_name: str,
) -> float:
    result = _finite(
        value,
        field_name,
    )

    if result <= 0.0:
        raise BlotIntegrationError(
            f"{field_name} must be positive"
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
class ReconstructionSessionRequest:
    source_digest: str
    source_kind: str = "raster"
    objective: str = (
        "recover the smallest semantically correct "
        "professionally constructed editable vector "
        "model capable of reproducing the recoverable "
        "visual information"
    )
    constraints: Mapping[str, Any] = field(
        default_factory=dict
    )
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.session-request",

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

        body["session_request_id"] = (
            "blot-session-request-"
            + _digest(body)[:24]
        )

        body["digest"] = _digest(body)

        return body

    def pipeline_request(
        self,
    ) -> ReconstructionRequest:
        return ReconstructionRequest(
            source_digest=self.source_digest,
            source_kind=self.source_kind,
            objective=self.objective,
            constraints=dict(
                self.constraints
            ),
            provenance=tuple(
                self.provenance
            ),
        )


@dataclass(frozen=True, slots=True)
class ProjectionReceipt:
    profile_id: str
    width: float
    height: float
    execution_contract_digest: str
    construction_digest: str
    svg_digest: str
    svg_document_digest: str
    projection_manifest_digest: str
    segue_id: str

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.projection-receipt",

            "profile_id":
                _text(
                    self.profile_id,
                    "profile_id",
                ),

            "width":
                _positive(
                    self.width,
                    "width",
                ),

            "height":
                _positive(
                    self.height,
                    "height",
                ),

            "execution_contract_digest":
                _text(
                    self.execution_contract_digest,
                    "execution_contract_digest",
                ),

            "construction_digest":
                _text(
                    self.construction_digest,
                    "construction_digest",
                ),

            "svg_digest":
                _text(
                    self.svg_digest,
                    "svg_digest",
                ),

            "svg_document_digest":
                _text(
                    self.svg_document_digest,
                    "svg_document_digest",
                ),

            "projection_manifest_digest":
                _text(
                    self.projection_manifest_digest,
                    "projection_manifest_digest",
                ),

            "segue_id":
                _text(
                    self.segue_id,
                    "segue_id",
                ),

            "projection_is_authority":
                False,

            "svg_is_derived":
                True,

            "authority_effect":
                "none",

            "mutation_effect":
                "none",

            "projection_only":
                True,
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class ProjectionArtifact:
    svg: str
    document: SvgDocument
    receipt: ProjectionReceipt

    def normalized(self) -> dict[str, Any]:
        document = self.document.normalized()
        receipt = self.receipt.normalized()

        svg_digest = _digest(
            self.svg
        )

        if (
            receipt[
                "svg_digest"
            ]
            != svg_digest
        ):
            raise BlotIntegrationError(
                "projection receipt svg digest "
                "does not match artifact"
            )

        if (
            receipt[
                "svg_document_digest"
            ]
            != document[
                "digest"
            ]
        ):
            raise BlotIntegrationError(
                "projection receipt document "
                "digest does not match artifact"
            )

        body = {
            "schema":
                f"{schema}.projection-artifact",

            "svg_digest":
                svg_digest,

            "document":
                document,

            "receipt":
                receipt,

            "projection_is_authority":
                False,

            "svg_is_derived":
                True,

            "authority_effect":
                "none",

            "mutation_effect":
                "none",

            "projection_only":
                True,
        }

        body["digest"] = _digest(body)

        return body


class BlotReconstructionRuntime:
    def __init__(
        self,
        request: ReconstructionSessionRequest,
        *,
        opus_adapter: OpusAIAdapter | None = None,
        projection_profiles: Iterable[
            ProjectionProfile
        ] | None = None,
    ) -> None:
        self.request = request

        self.pipeline = BlotPipeline(
            request.pipeline_request(),
            opus_adapter=opus_adapter,
            projection_profiles=(
                projection_profiles
                if projection_profiles
                is not None
                else default_projection_profiles()
            ),
        )

        self._artifacts: dict[
            str,
            ProjectionArtifact,
        ] = {}

    def add_evidence(
        self,
        evidence: Evidence,
    ) -> str:
        return self.pipeline.add_evidence(
            evidence
        )

    def substantiate(
        self,
        primitive: ConstructionPrimitive,
    ) -> str:
        return self.pipeline.substantiate(
            primitive
        )

    def relate(
        self,
        segue: ConstructionSegue,
    ) -> str:
        return self.pipeline.relate(
            segue
        )

    def add_candidate(
        self,
        candidate: Candidate,
    ) -> str:
        return self.pipeline.add_candidate(
            candidate
        )

    def work_for_rung(
        self,
        rung: int,
    ) -> tuple[
        OpusWorkUnit,
        ...
    ]:
        return self.pipeline.work_for_rung(
            rung
        )

    def opus_requests(
        self,
        rung: int,
    ) -> tuple[
        dict[str, Any],
        ...
    ]:
        return self.pipeline.opus_requests(
            rung
        )

    def opus_selection_packet(
        self,
        work: OpusWorkUnit,
    ) -> dict[str, Any]:
        return (
            self.pipeline
            .opus_selection_packet(
                work
            )
        )

    def record_opus_result(
        self,
        work: OpusWorkUnit,
        *,
        status: str,
        output: Mapping[str, Any],
        attempt: int = 1,
        confidence: float = 1.0,
        causal_stage_id: str | None = None,
        provider: str | None = None,
        mode: str | None = None,
        provenance: Iterable[str] = (),
    ) -> dict[str, Any]:
        return (
            self.pipeline
            .record_opus_result(
                work,
                status=status,
                output=output,
                attempt=attempt,
                confidence=confidence,
                causal_stage_id=(
                    causal_stage_id
                ),
                provider=provider,
                mode=mode,
                provenance=provenance,
            )
        )

    def select_construction(
        self,
    ) -> str:
        selected = (
            self.pipeline
            .select_construction()
        )

        return selected.candidate_id

    def compile_execution(
        self,
        candidate_id: str,
        steps: Iterable[
            ExecutionStep
        ],
    ) -> ExecutionContract:
        return (
            self.pipeline
            .compile_execution(
                candidate_id,
                tuple(steps),
            )
        )

    def execution_contract(
        self,
    ) -> ExecutionContract:
        return (
            self.pipeline
            .execution_contract()
        )

    def projection_builder(
        self,
        profile_id: str,
        *,
        width: float,
        height: float,
        view_box: tuple[
            float,
            float,
            float,
            float,
        ] | None = None,
    ) -> ProjectionBuilder:
        self.pipeline.profile(
            profile_id
        )

        contract = (
            self.execution_contract()
        )

        return ProjectionBuilder(
            contract,
            width=width,
            height=height,
            view_box=view_box,
            profile=profile_id,
        )

    def project(
        self,
        profile_id: str,
        *,
        width: float,
        height: float,
        primitives: Iterable[
            ConstructionPrimitive
        ] = (),
        paths: Iterable[
            SvgPath
        ] = (),
        groups: Iterable[
            SvgGroup
        ] = (),
        linear_gradients: Iterable[
            SvgLinearGradient
        ] = (),
        radial_gradients: Iterable[
            SvgRadialGradient
        ] = (),
        clip_paths: Iterable[
            SvgClipPath
        ] = (),
        masks: Iterable[
            SvgMask
        ] = (),
        primitive_paint: Mapping[
            str,
            Mapping[str, Any]
        ] | None = None,
        view_box: tuple[
            float,
            float,
            float,
            float,
        ] | None = None,
        metadata: Mapping[
            str,
            Any
        ] | None = None,
    ) -> ProjectionArtifact:
        width = _positive(
            width,
            "width",
        )

        height = _positive(
            height,
            "height",
        )

        profile = self.pipeline.profile(
            profile_id
        )

        projection_request = (
            self.pipeline
            .projection_request(
                profile_id,
                width=width,
                height=height,
            )
        )

        builder = self.projection_builder(
            profile_id,
            width=width,
            height=height,
            view_box=view_box,
        )

        for gradient in linear_gradients:
            builder.add_linear_gradient(
                gradient
            )

        for gradient in radial_gradients:
            builder.add_radial_gradient(
                gradient
            )

        for clip_path in clip_paths:
            builder.add_clip_path(
                clip_path
            )

        for mask in masks:
            builder.add_mask(
                mask
            )

        paints = dict(
            primitive_paint or {}
        )

        for primitive in primitives:
            primitive_data = (
                primitive.normalized()
            )

            primitive_id = (
                primitive_data[
                    "primitive_id"
                ]
            )

            paint = dict(
                paints.get(
                    primitive_id,
                    {},
                )
            )

            builder.project_primitive(
                primitive,
                fill=str(
                    paint.get(
                        "fill",
                        "none",
                    )
                ),
                stroke=(
                    str(
                        paint[
                            "stroke"
                        ]
                    )
                    if paint.get(
                        "stroke"
                    )
                    is not None
                    else None
                ),
                stroke_width=(
                    float(
                        paint[
                            "stroke_width"
                        ]
                    )
                    if paint.get(
                        "stroke_width"
                    )
                    is not None
                    else None
                ),
                opacity=float(
                    paint.get(
                        "opacity",
                        1.0,
                    )
                ),
            )

        for path in paths:
            builder.add_path(
                path
            )

        for group in groups:
            builder.add_group(
                group
            )

        projection
