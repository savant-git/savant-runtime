#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


name = "blot."
schema = "savant.translucent.blot.reconstruction.v2"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

max_candidates = 16
max_stage_attempts = 3
max_dependencies = 256
max_evidence = 4096
max_primitives = 8192
max_ambiguities = 1024
max_segues = 16384
max_stage_results = 16384
max_execution_steps = 8192


class BlotReconstructionError(RuntimeError):
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
        raw = _canonical(value).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _text(value: Any, field_name: str) -> str:
    result = str(value or "").strip()

    if not result:
        raise BlotReconstructionError(
            f"{field_name} is required"
        )

    return result


def _confidence(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise BlotReconstructionError(
            "confidence must be numeric"
        ) from exc

    if not math.isfinite(result):
        raise BlotReconstructionError(
            "confidence must be finite"
        )

    if result < 0.0 or result > 1.0:
        raise BlotReconstructionError(
            "confidence must be between 0 and 1"
        )

    return result


def _unique_text(
    values: Iterable[Any],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(value).strip()
            for value in values
            if str(value).strip()
        )
    )


def _finite_mapping(
    value: Mapping[str, Any],
    field_name: str,
) -> dict[str, float]:
    result: dict[str, float] = {}

    for key, raw in sorted(value.items()):
        try:
            number = float(raw)
        except (TypeError, ValueError) as exc:
            raise BlotReconstructionError(
                f"{field_name}.{key} must be numeric"
            ) from exc

        if not math.isfinite(number):
            raise BlotReconstructionError(
                f"{field_name}.{key} must be finite"
            )

        result[str(key)] = number

    return result


@dataclass(frozen=True, slots=True)
class Stage:
    stage_id: str
    rung: int
    ordinal: int
    name: str
    capability: str
    dependencies: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        if self.rung not in {1, 2, 3}:
            raise BlotReconstructionError(
                "stage rung must be 1, 2, or 3"
            )

        if self.ordinal < 1:
            raise BlotReconstructionError(
                "stage ordinal must be positive"
            )

        dependencies = _unique_text(
            self.dependencies
        )

        if len(dependencies) > max_dependencies:
            raise BlotReconstructionError(
                "stage dependency limit exceeded"
            )

        body = {
            "stage_id":
                _text(
                    self.stage_id,
                    "stage_id",
                ),

            "rung":
                int(self.rung),

            "ordinal":
                int(self.ordinal),

            "name":
                _text(
                    self.name,
                    "name",
                ),

            "capability":
                _text(
                    self.capability,
                    "capability",
                ),

            "dependencies":
                list(dependencies),
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    kind: str
    payload: Mapping[str, Any]
    confidence: float
    provenance: tuple[str, ...] = ()
    state: str = "observed"

    def normalized(self) -> dict[str, Any]:
        if self.state not in {
            "observed",
            "constrained",
            "inferred",
            "ambiguous",
            "authored",
        }:
            raise BlotReconstructionError(
                f"invalid evidence state: {self.state}"
            )

        body = {
            "schema":
                f"{schema}.evidence",

            "evidence_id":
                _text(
                    self.evidence_id,
                    "evidence_id",
                ),

            "kind":
                _text(
                    self.kind,
                    "kind",
                ),

            "payload":
                dict(self.payload),

            "confidence":
                _confidence(self.confidence),

            "state":
                self.state,

            "provenance":
                list(
                    _unique_text(
                        self.provenance
                    )
                ),

            "authority_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class Ambiguity:
    ambiguity_id: str
    subject: str
    description: str
    blocking: bool
    earliest_stage_id: str
    alternatives: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.0

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.ambiguity",

            "ambiguity_id":
                _text(
                    self.ambiguity_id,
                    "ambiguity_id",
                ),

            "subject":
                _text(
                    self.subject,
                    "subject",
                ),

            "description":
                _text(
                    self.description,
                    "description",
                ),

            "blocking":
                bool(self.blocking),

            "earliest_stage_id":
                _text(
                    self.earliest_stage_id,
                    "earliest_stage_id",
                ),

            "alternatives":
                list(
                    _unique_text(
                        self.alternatives
                    )
                ),

            "evidence_ids":
                list(
                    _unique_text(
                        self.evidence_ids
                    )
                ),

            "confidence":
                _confidence(self.confidence),

            "authority_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class ConstructionPrimitive:
    primitive_id: str
    kind: str
    parameters: Mapping[str, Any]
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 1.0
    state: str = "inferred"
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        if self.state not in {
            "observed",
            "constrained",
            "inferred",
            "ambiguous",
            "authored",
        }:
            raise BlotReconstructionError(
                f"invalid primitive state: {self.state}"
            )

        body = {
            "schema":
                f"{schema}.construction-primitive",

            "primitive_id":
                _text(
                    self.primitive_id,
                    "primitive_id",
                ),

            "kind":
                _text(
                    self.kind,
                    "kind",
                ),

            "parameters":
                dict(self.parameters),

            "evidence_ids":
                list(
                    _unique_text(
                        self.evidence_ids
                    )
                ),

            "confidence":
                _confidence(self.confidence),

            "state":
                self.state,

            "lineage":
                list(
                    _unique_text(
                        self.lineage
                    )
                ),

            "provenance":
                list(
                    _unique_text(
                        self.provenance
                    )
                ),

            "authority_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class ConstructionSegue:
    kind: str
    source: str
    target: str
    parameters: Mapping[str, Any] = field(
        default_factory=dict
    )
    lineage: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.construction-segue",

            "kind":
                _text(
                    self.kind,
                    "kind",
                ),

            "source":
                _text(
                    self.source,
                    "source",
                ),

            "target":
                _text(
                    self.target,
                    "target",
                ),

            "parameters":
                dict(self.parameters),

            "lineage":
                list(
                    _unique_text(
                        self.lineage
                    )
                ),

            "provenance":
                list(
                    _unique_text(
                        self.provenance
                    )
                ),

            "authority_effect":
                "none",
        }

        body["segue_id"] = (
            "blot-construction-segue-"
            + _digest(body)[:24]
        )

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class Candidate:
    candidate_id: str
    strategy: str
    primitive_ids: tuple[str, ...]
    predicted_cost: Mapping[str, float]
    predicted_quality: Mapping[str, float]
    blockers: tuple[str, ...] = ()
    segue_ids: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.candidate",

            "candidate_id":
                _text(
                    self.candidate_id,
                    "candidate_id",
                ),

            "strategy":
                _text(
                    self.strategy,
                    "strategy",
                ),

            "primitive_ids":
                list(
                    _unique_text(
                        self.primitive_ids
                    )
                ),

            "segue_ids":
                list(
                    _unique_text(
                        self.segue_ids
                    )
                ),

            "predicted_cost":
                _finite_mapping(
                    self.predicted_cost,
                    "predicted_cost",
                ),

            "predicted_quality":
                _finite_mapping(
                    self.predicted_quality,
                    "predicted_quality",
                ),

            "blockers":
                list(
                    _unique_text(
                        self.blockers
                    )
                ),

            "provenance":
                list(
                    _unique_text(
                        self.provenance
                    )
                ),

            "authority_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class OpusWorkUnit:
    work_id: str
    stage_id: str
    capability: str
    instruction: str
    dependencies: tuple[str, ...] = ()
    preferred_providers: tuple[str, ...] = ()
    input_digest: str = ""
    context: Mapping[str, Any] = field(
        default_factory=dict
    )

    def normalized(self) -> dict[str, Any]:
        dependencies = _unique_text(
            self.dependencies
        )

        if len(dependencies) > max_dependencies:
            raise BlotReconstructionError(
                "work dependency limit exceeded"
            )

        body = {
            "schema":
                f"{schema}.opus-work-unit",

            "work_id":
                _text(
                    self.work_id,
                    "work_id",
                ),

            "stage_id":
                _text(
                    self.stage_id,
                    "stage_id",
                ),

            "capability":
                _text(
                    self.capability,
                    "capability",
                ),

            "instruction":
                _text(
                    self.instruction,
                    "instruction",
                ),

            "dependencies":
                list(dependencies),

            "preferred_providers":
                list(
                    _unique_text(
                        self.preferred_providers
                    )
                ),

            "input_digest":
                str(self.input_digest),

            "context":
                dict(self.context),

            "execution_owner":
                "opus",

            "routing_owner":
                "opus",

            "authority_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class StageResult:
    stage_id: str
    attempt: int
    status: str
    output: Mapping[str, Any]
    input_digest: str
    confidence: float = 1.0
    causal_stage_id: str | None = None
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        if self.attempt < 1:
            raise BlotReconstructionError(
                "stage attempt must be positive"
            )

        if self.attempt > max_stage_attempts:
            raise BlotReconstructionError(
                "stage attempt limit exceeded"
            )

        if self.status not in {
            "accepted",
            "rejected",
            "blocked",
            "ambiguous",
        }:
            raise BlotReconstructionError(
                f"invalid stage status: {self.status}"
            )

        body = {
            "schema":
                f"{schema}.stage-result",

            "stage_id":
                _text(
                    self.stage_id,
                    "stage_id",
                ),

            "attempt":
                int(self.attempt),

            "status":
                self.status,

            "output":
                dict(self.output),

            "input_digest":
                _text(
                    self.input_digest,
                    "input_digest",
                ),

            "confidence":
                _confidence(self.confidence),

            "causal_stage_id":
                self.causal_stage_id,

            "provenance":
                list(
                    _unique_text(
                        self.provenance
                    )
                ),

            "authority_effect":
                "none",
        }

        body["cache_key"] = _digest(
            {
                "stage_id":
                    body["stage_id"],

                "input_digest":
                    body["input_digest"],
            }
        )

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    step_id: str
    stage_id: str
    operation: str
    primitive_ids: tuple[str, ...] = ()
    segue_ids: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    parameters: Mapping[str, Any] = field(
        default_factory=dict
    )

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.execution-step",

            "step_id":
                _text(
                    self.step_id,
                    "step_id",
                ),

            "stage_id":
                _text(
                    self.stage_id,
                    "stage_id",
                ),

            "operation":
                _text(
                    self.operation,
                    "operation",
                ),

            "primitive_ids":
                list(
                    _unique_text(
                        self.primitive_ids
                    )
                ),

            "segue_ids":
                list(
                    _unique_text(
                        self.segue_ids
                    )
                ),

            "dependencies":
                list(
                    _unique_text(
                        self.dependencies
                    )
                ),

            "parameters":
                dict(self.parameters),

            "authority_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class ExecutionContract:
    candidate_id: str
    construction_digest: str
    steps: tuple[ExecutionStep, ...]
    topology_resolved: bool
    geometry_resolved: bool
    negative_space_resolved: bool
    booleans_resolved: bool
    materials_resolved: bool
    lighting_resolved: bool
    masks_resolved: bool
    gradients_resolved: bool
    ambiguous: tuple[str, ...]
    blocking_ambiguities: int
    predicted_counts: Mapping[str, int]
    execution_ready: bool

    def normalized(self) -> dict[str, Any]:
        counts: dict[str, int] = {}

        for key, value in sorted(
            self.predicted_counts.items()
        ):
            number = int(value)

            if number < 0:
                raise BlotReconstructionError(
                    "predicted counts cannot "
                    "be negative"
                )

            counts[str(key)] = number

        body = {
            "schema":
                f"{schema}.execution-contract",

            "candidate_id":
                _text(
                    self.candidate_id,
                    "candidate_id",
                ),

            "construction_digest":
                _text(
                    self.construction_digest,
                    "construction_digest",
                ),

            "steps":
                [
                    step.normalized()
                    for step in self.steps
                ],

            "topology_resolved":
                bool(self.topology_resolved),

            "geometry_resolved":
                bool(self.geometry_resolved),

            "negative_space_resolved":
                bool(
                    self.negative_space_resolved
                ),

            "booleans_resolved":
                bool(self.booleans_resolved),

            "materials_resolved":
                bool(self.materials_resolved),

            "lighting_resolved":
                bool(self.lighting_resolved),

            "masks_resolved":
                bool(self.masks_resolved),

            "gradients_resolved":
                bool(self.gradients_resolved),

            "ambiguous":
                list(
                    _unique_text(
                        self.ambiguous
                    )
                ),

            "blocking_ambiguities":
                int(
                    self.blocking_ambiguities
                ),

            "predicted_counts":
                counts,

            "execution_ready":
                bool(self.execution_ready),

            "authority_effect":
                "none",

            "mutation_effect":
                "none",

            "projection_only":
                True,
        }

        body["digest"] = _digest(body)

        return body


def _stage(
    rung: int,
    ordinal: int,
    stage_id: str,
    stage_name: str,
    capability: str,
    dependencies: Sequence[str] = (),
) -> Stage:
    return Stage(
        stage_id=stage_id,
        rung=rung,
        ordinal=ordinal,
        name=stage_name,
        capability=capability,
        dependencies=tuple(dependencies),
    )


_rung_1_names = (
    "source normalization",
    "raster-artifact assessment",
    "visual-hierarchy decomposition",
    "topology inference",
    "semantic object segmentation",
    "occlusion analysis",
    "symmetry detection",
    "geometric scaffold recovery",
    "primitive classification",
    "curve reconstruction planning",
    "curvature/continuity analysis",
    "negative-space reconstruction",
    "stroke-versus-fill inference",
    "boolean-construction analysis",
    "canonical geometry synthesis planning",
    "shape-economy analysis",
    "base-color reconstruction",
    "palette relationship analysis",
    "gradient-field analysis",
    "gradient-construction planning",
    "material inference",
    "surface-orientation inference",
    "lighting decomposition",
    "highlight reconstruction analysis",
    "shadow reconstruction analysis",
    "bevel/depth reconstruction",
    "mask/clipping analysis",
    "texture abstraction",
    "svg tool selection",
    "optical-size projection planning",
    "perceptual reconstruction specification",
    "structural quality specification",
)

_rung_2_names = (
    "construction-graph integrity",
    "ambiguity inventory",
    "confidence propagation",
    "tool feasibility",
    "renderer compatibility simulation",
    "primitive instantiation simulation",
    "anchor-placement rehearsal",
    "continuity rehearsal",
    "boolean rehearsal",
    "compound-path rehearsal",
    "transform rehearsal",
    "negative-space verification",
    "self-intersection prediction",
    "winding-rule verification",
    "degenerate-geometry detection",
    "material-response simulation",
    "lighting simulation",
    "gradient-placement simulation",
    "highlight-placement simulation",
    "shadow projection simulation",
    "mask interaction simulation",
    "clipping interaction simulation",
    "transparency/compositing simulation",
    "stroke expansion simulation",
    "complexity budget",
    "redundancy forecast",
    "failure-mode prediction",
    "execution-plan compilation",
)

_rung_3_names = (
    "initialize svg document/coordinate system",
    "instantiate scaffold",
    "canonical centerlines",
    "primary bezier silhouettes",
    "curve constraints",
    "symmetry-derived geometry",
    "negative spaces",
    "compound paths",
    "booleans",
    "secondary/inset geometry",
    "strokes",
    "winding/topology normalize",
    "palette tokens",
    "material definitions",
    "base fills",
    "linear gradients",
    "radial/focal gradients",
    "gradient transforms",
    "material overlays",
    "key-light response",
    "fill-light response",
    "specular highlights",
    "rim lighting",
    "self-shadow",
    "cast/contact shadows",
    "bevel/depth",
    "clipping paths",
    "masks",
    "restrained filters/effects",
    "final z-order/compositing graph",
    "canonical presentation svg",
    "derive flat/monochrome/standard/micro projections",
)


def _slug(value: str) -> str:
    result = []

    previous_dash = False

    for character in value.lower():
        if character.isalnum():
            result.append(character)
            previous_dash = False
        elif not previous_dash:
            result.append("-")
            previous_dash = True

    return "".join(result).strip("-")


def _build_stages(
    rung: int,
    names: Sequence[str],
    capability: str,
) -> tuple[Stage, ...]:
    stages: list[Stage] = []

    previous: str | None = None

    for ordinal, stage_name in enumerate(
        names,
        start=1,
    ):
        stage_id = (
            f"r{rung}-{ordinal:02d}-"
            f"{_slug(stage_name)}"
        )

        dependencies = (
            (previous,)
            if previous is not None
            else ()
        )

        stages.append(
            _stage(
                rung,
                ordinal,
                stage_id,
                stage_name,
                capability,
                dependencies,
            )
        )

        previous = stage_id

    return tuple(stages)


rung_1_stages = _build_stages(
    1,
    _rung_1_names,
    "vision-analysis",
)

rung_2_stages = _build_stages(
    2,
    _rung_2_names,
    "geometry-reasoning",
)

rung_3_stages = _build_stages(
    3,
    _rung_3_names,
    "vector-construction",
)

all_stages = (
    rung_1_stages
    + rung_2_stages
    + rung_3_stages
)

verification_lock = (
    "topology",
    "silhouette",
    "landmarks",
    "negative-space",
    "curvature",
    "proportions",
    "color",
    "gradients",
    "material-appearance",
    "lighting",
    "masks",
    "clipping",
    "optical-size-behavior",
    "editability",
    "primitive-count",
    "anchor-economy",
    "renderer-stability",
    "deterministic-replay",
    "lineage",
    "provenance",
)


class ReconstructionPipeline:
    def __init__(
        self,
        source_digest: str,
    ) -> None:
        self.source_digest = _text(
            source_digest,
            "source_digest",
        )

        self._evidence: dict[
            str,
            Evidence,
        ] = {}

        self._ambiguities: dict[
            str,
            Ambiguity,
        ] = {}

        self._primitives: dict[
            str,
            ConstructionPrimitive,
        ] = {}

        self._segues: dict[
            str,
            ConstructionSegue,
        ] = {}

        self._candidates: dict[
            str,
            Candidate,
        ] = {}

        self._stage_results: dict[
            tuple[str, int],
            StageResult,
        ] = {}

        self._stage_index = {
            stage.stage_id:
                stage
            for stage in all_stages
        }

    def add_evidence(
        self,
        evidence: Evidence,
    ) -> str:
        if (
            evidence.evidence_id
            not in self._evidence
            and len(self._evidence)
            >= max_evidence
        ):
            raise BlotReconstructionError(
                "evidence limit exceeded"
            )

        normalized = evidence.normalized()
        evidence_id = normalized[
            "evidence_id"
        ]

        existing = self._evidence.get(
            evidence_id
        )

        if (
            existing is not None
            and existing.normalized()
            != normalized
        ):
            raise BlotReconstructionError(
                "evidence identity conflict: "
                f"{evidence_id}"
            )

        self._evidence[
            evidence_id
        ] = evidence

        return evidence_id

    def add_ambiguity(
        self,
        ambiguity: Ambiguity,
    ) -> str:
        if (
            ambiguity.ambiguity_id
            not in self._ambiguities
            and len(self._ambiguities)
            >= max_ambiguities
        ):
            raise BlotReconstructionError(
                "ambiguity limit exceeded"
            )

        normalized = ambiguity.normalized()

        if (
            normalized[
                "earliest_stage_id"
            ]
            not in self._stage_index
        ):
            raise BlotReconstructionError(
                "ambiguity references unknown "
                "causal stage"
            )

        for evidence_id in normalized[
            "evidence_ids"
        ]:
            if evidence_id not in self._evidence:
                raise BlotReconstructionError(
                    "ambiguity references unknown "
                    f"evidence: {evidence_id}"
                )

        ambiguity_id = normalized[
            "ambiguity_id"
        ]

        existing = self._ambiguities.get(
            ambiguity_id
        )

        if (
            existing is not None
            and existing.normalized()
            != normalized
        ):
            raise BlotReconstructionError(
                "ambiguity identity conflict: "
                f"{ambiguity_id}"
            )

        self._ambiguities[
            ambiguity_id
        ] = ambiguity

        return ambiguity_id

    def substantiate(
        self,
        primitive: ConstructionPrimitive,
    ) -> str:
        if (
            primitive.primitive_id
            not in self._primitives
            and len(self._primitives)
            >= max_primitives
        ):
            raise BlotReconstructionError(
                "primitive limit exceeded"
            )

        normalized = primitive.normalized()

        for evidence_id in normalized[
            "evidence_ids"
        ]:
            if evidence_id not in self._evidence:
                raise BlotReconstructionError(
                    "primitive references unknown "
                    f"evidence: {evidence_id}"
                )

        primitive_id = normalized[
            "primitive_id"
        ]

        existing = self._primitives.get(
            primitive_id
        )

        if (
            existing is not None
            and existing.normalized()
            != normalized
        ):
            raise BlotReconstructionError(
                "primitive identity conflict: "
                f"{primitive_id}"
            )

        self._primitives[
            primitive_id
        ] = primitive

        return primitive_id

    def relate(
        self,
        segue: ConstructionSegue,
    ) -> str:
        if len(self._segues) >= max_segues:
            raise BlotReconstructionError(
                "construction segue limit exceeded"
            )

        normalized = segue.normalized()

        source = normalized["source"]
        target = normalized["target"]

        if source not in self._primitives:
            raise BlotReconstructionError(
                f"unknown segue source: {source}"
            )

        if target not in self._primitives:
            raise BlotReconstructionError(
                f"unknown segue target: {target}"
            )

        segue_id = normalized[
            "segue_id"
        ]

        existing = self._segues.get(
            segue_id
        )

        if (
            existing is not None
            and existing.normalized()
            != normalized
        ):
            raise BlotReconstructionError(
                "construction segue identity "
                "conflict"
            )

        self._segues[
            segue_id
        ] = segue

        return segue_id

    def add_candidate(
        self,
        candidate: Candidate,
    ) -> str:
        if (
            candidate.candidate_id
            not in self._candidates
            and len(self._candidates)
            >= max_candidates
        ):
            raise BlotReconstructionError(
                "candidate limit exceeded"
            )

        normalized = candidate.normalized()

        for primitive_id in normalized[
            "primitive_ids"
        ]:
            if primitive_id not in self._primitives:
                raise BlotReconstructionError(
                    "candidate references unknown "
                    f"primitive: {primitive_id}"
                )

        for segue_id in normalized[
            "segue_ids"
        ]:
            if segue_id not in self._segues:
                raise BlotReconstructionError(
                    "candidate references unknown "
                    f"segue: {segue_id}"
                )

        candidate_id = normalized[
            "candidate_id"
        ]

        existing = self._candidates.get(
            candidate_id
        )

        if (
            existing is not None
            and existing.normalized()
            != normalized
        ):
            raise BlotReconstructionError(
                "candidate identity conflict: "
                f"{candidate_id}"
            )

        self._candidates[
            candidate_id
        ] = candidate

        return candidate_id

    def record_stage_result(
        self,
        result: StageResult,
    ) -> str:
        if (
            len(self._stage_results)
            >= max_stage_results
        ):
            raise BlotReconstructionError(
                "stage result limit exceeded"
            )

        normalized = result.normalized()

        stage_id = normalized[
            "stage_id"
        ]

        if stage_id not in self._stage_index:
            raise BlotReconstructionError(
                f"unknown stage: {stage_id}"
            )

        causal = normalized[
            "causal_stage_id"
        ]

        if (
            causal is not None
            and causal not in self._stage_index
        ):
            raise BlotReconstructionError(
                "unknown causal stage: "
                f"{causal}"
            )

        key = (
            stage_id,
            normalized["attempt"],
        )

        existing = self._stage_results.get(
            key
        )

        if (
            existing is not None
            and existing.normalized()
            != normalized
        ):
            raise BlotReconstructionError(
                "stage result identity conflict"
            )

        self._stage_results[
            key
        ] = result

        return normalized["digest"]

    def construction_graph(
        self,
    ) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.construction-graph",

            "source_digest":
                self.source_digest,

            "evidence":
                [
                    self._evidence[
                        evidence_id
                    ].normalized()
                    for evidence_id
                    in sorted(
                        self._evidence
                    )
                ],

            "ambiguities":
                [
                    self._ambiguities[
                        ambiguity_id
                    ].normalized()
                    for ambiguity_id
                    in sorted(
                        self._ambiguities
                    )
                ],

            "primitives":
                [
                    self._primitives[
                        primitive_id
                    ].normalized()
                    for primitive_id
                    in sorted(
                        self._primitives
                    )
                ],

            "segues":
                [
                    self._segues[
                        segue_id
                    ].normalized()
                    for segue_id
                    in sorted(
                        self._segues
                    )
                ],

            "representation":
                (
                    "semantic sparse "
                    "construction graph"
                ),

            "instance_first":
                True,

            "typed_segues":
                True,

            "geometry_owns_shape":
                True,

            "materials_decorate":
                True,

            "authority_effect":
                "none",

            "projection_only":
                True,
        }

        body["digest"] = _digest(body)

        return body

    def opus_plan(
        self,
        rung: int,
    ) -> tuple[
        OpusWorkUnit,
        ...
    ]:
        if rung not in {1, 2, 3}:
            raise BlotReconstructionError(
                "rung must be 1, 2, or 3"
            )

        graph = self.construction_graph()

        stages = tuple(
            stage
            for stage in all_stages
            if stage.rung == rung
        )

        work_ids = {
            stage.stage_id:
                (
                    "blot-work-"
                    + _digest(
                        {
                            "source":
                                self.source_digest,

                            "stage":
                                stage.normalized(),

                            "graph":
                                graph["digest"],
                        }
                    )[:24]
                )
            for stage in stages
        }

        result: list[
            OpusWorkUnit
        ] = []

        for stage in stages:
            dependencies = tuple(
                work_ids[dependency]
                for dependency
                in stage.dependencies
                if dependency in work_ids
            )

            unit = OpusWorkUnit(
                work_id=work_ids[
                    stage.stage_id
                ],
                stage_id=stage.stage_id,
                capability=stage.capability,
                instruction=(
                    f"Execute blot. reconstruction "
                    f"stage {stage.ordinal} of rung "
                    f"{stage.rung}: {stage.name}. "
                    "Preserve evidence state, "
                    "confidence, lineage, provenance, "
                    "semantic economy, topology, "
                    "editability, and deterministic "
                    "replay. Do not create authority."
                ),
                dependencies=dependencies,
                input_digest=graph[
                    "digest"
                ],
                context={
                    "rung":
                        stage.rung,

                    "ordinal":
                        stage.ordinal,

                    "stage_name":
                        stage.name,

                    "construction_digest":
                        graph["digest"],

                    "source_digest":
                        self.source_digest,
                },
            )

            result.append(unit)

        return tuple(result)

    def opus_packet(
        self,
        rung: int,
    ) -> dict[str, Any]:
        work = [
            unit.normalized()
            for unit in self.opus_plan(
                rung
            )
        ]

        body = {
            "schema":
                f"{schema}.opus-packet",

            "owner":
                "blot.",

            "orchestrator":
                "opus",

            "execution_owner":
                "opus",

            "routing_owner":
                "opus",

            "rung":
                rung,

            "construction":
                self.construction_graph(),

            "work":
                work,

            "authority_effect":
                "none",

            "mutation_effect":
                "none",

            "projection_only":
                True,
        }

        body["digest"] = _digest(body)

        return body

    def dry_run(
        self,
        candidate_id: str,
    ) -> dict[str, Any]:
        candidate_id = _text(
            candidate_id,
            "candidate_id",
        )

        candidate = self._candidates.get(
            candidate_id
        )

        if candidate is None:
            raise BlotReconstructionError(
                f"unknown candidate: {candidate_id}"
            )

        normalized = candidate.normalized()

        blocking_ambiguities = [
            ambiguity.normalized()
            for ambiguity
            in self._ambiguities.values()
            if ambiguity.blocking
        ]

        blockers = list(
            normalized[
                "blockers"
            ]
        )

        blockers.extend(
            ambiguity[
                "ambiguity_id"
            ]
            for ambiguity
            in blocking_ambiguities
        )

        cost = normalized[
            "predicted_cost"
        ]

        predicted_counts = {
            "paths":
                max(
                    0,
                    int(
                        round(
                            cost.get(
                                "paths",
                                0.0,
                            )
                        )
                    ),
                ),

            "anchors":
                max(
                    0,
                    int(
                        round(
                            cost.get(
                                "anchors",
                                0.0,
                            )
                        )
                    ),
                ),

            "gradients":
                max(
                    0,
                    int(
                        round(
                            cost.get(
                                "gradients",
                                0.0,
                            )
                        )
                    ),
                ),

            "masks":
                max(
                    0,
                    int(
                        round(
                            cost.get(
                                "masks",
                                0.0,
                            )
                        )
                    ),
                ),

            "clips":
                max(
                    0,
                    int(
                        round(
                            cost.get(
                                "clips",
                                0.0,
                            )
                        )
                    ),
                ),

            "filters":
                max(
                    0,
                    int(
                        round(
                            cost.get(
                                "filters",
                                0.0,
                            )
                        )
                    ),
                ),
        }

        graph = self.construction_graph()

        result = {
            "schema":
                f"{schema}.dry-run",

            "candidate":
                normalized,

            "construction_digest":
                graph["digest"],

            "blocking_ambiguities":
                len(
                    blocking_ambiguities
                ),

            "blockers":
                list(
                    _unique_text(
                        blockers
                    )
                ),

            "predicted_counts":
                predicted_counts,

            "execution_ready":
                not blockers,

            "authority_effect":
                "none",
        }

        result["digest"] = _digest(
            result
        )

        return result

    def compile_execution_contract(
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

        candidate = self._candidates.get(
            candidate_id
        )

        if candidate is None:
            raise BlotReconstructionError(
                f"unknown candidate: {candidate_id}"
            )

        step_tuple = tuple(steps)

        if (
            len(step_tuple)
            > max_execution_steps
        ):
            raise BlotReconstructionError(
                "execution step limit exceeded"
            )

        step_ids: set[str] = set()

        for step in step_tuple:
            normalized = step.normalized()

            step_id = normalized[
                "step_id"
            ]

            if step_id in step_ids:
                raise BlotReconstructionError(
                    "duplicate execution step: "
                    f"{step_id}"
                )

            step_ids.add(step_id)

            stage_id = normalized[
                "stage_id"
            ]

            if stage_id not in self._stage_index:
                raise BlotReconstructionError(
                    "execution step references "
                    f"unknown stage: {stage_id}"
                )

            for primitive_id in normalized[
                "primitive_ids"
            ]:
                if primitive_id not in self._primitives:
                    raise BlotReconstructionError(
                        "execution step references "
                        "unknown primitive: "
                        f"{primitive_id}"
                    )

            for segue_id in normalized[
                "segue_ids"
            ]:
                if segue_id not in self._segues:
                    raise BlotReconstructionError(
                        "execution step references "
                        "unknown segue: "
                        f"{segue_id}"
                    )

        for step in step_tuple:
            normalized = step.normalized()

            for dependency in normalized[
                "dependencies"
            ]:
                if dependency not in step_ids:
                    raise BlotReconstructionError(
                        "execution step references "
                        "unknown dependency: "
                        f"{dependency}"
                    )

        dry_run = self.dry_run(
            candidate_id
        )

        blocking = [
            ambiguity.normalized()
            for ambiguity
            in self._ambiguities.values()
            if ambiguity.blocking
        ]

        blocking_subjects = {
            ambiguity[
                "subject"
            ].lower()
            for ambiguity
            in blocking
        }

        candidate_data = (
            candidate.normalized()
        )

        blockers = candidate_data[
            "blockers"
        ]

        topology_resolved = (
            "topology" not in blocking_subjects
        )

        geometry_resolved = (
            "geometry" not in blocking_subjects
        )

        negative_space_resolved = (
            "negative-space"
            not in blocking_subjects
            and "negative space"
            not in blocking_subjects
        )

        booleans_resolved = (
            "booleans" not in blocking_subjects
            and "boolean" not in blocking_subjects
        )

        materials_resolved = (
            "materials" not in blocking_subjects
            and "material" not in blocking_subjects
        )

        lighting_resolved = (
            "lighting" not in blocking_subjects
            and "light" not in blocking_subjects
        )

        masks_resolved = (
            "masks" not in blocking_subjects
            and "mask" not in blocking_subjects
        )

        gradients_resolved = (
            "gradients" not in blocking_subjects
            and "gradient" not in blocking_subjects
        )

        blocking_count = (
            len(blocking)
            + len(blockers)
        )

        execution_ready = (
            topology_resolved
            and geometry_resolved
            and negative_space_resolved
            and booleans_resolved
            and materials_resolved
            and lighting_resolved
            and masks_resolved
            and gradients_resolved
            and blocking_count == 0
            and dry_run[
                "execution_ready"
            ]
            is True
        )

        return ExecutionContract(
            candidate_id=candidate_id,
            construction_digest=(
                self.construction_graph()[
                    "digest"
                ]
            ),
            steps=step_tuple,
            topology_resolved=(
                topology_resolved
            ),
            geometry_resolved=(
                geometry_resolved
            ),
            negative_space_resolved=(
                negative_space_resolved
            ),
            booleans_resolved=(
                booleans_resolved
            ),
            materials_resolved=(
                materials_resolved
            ),
            lighting_resolved=(
                lighting_resolved
            ),
            masks_resolved=(
                masks_resolved
            ),
            gradients_resolved=(
                gradients_resolved
            ),
            ambiguous=tuple(
                ambiguity[
                    "ambiguity_id"
                ]
                for ambiguity
                in sorted(
                    (
                        item.normalized()
                        for item
                        in self._ambiguities.values()
                    ),
                    key=lambda item:
                        item[
                            "ambiguity_id"
                        ],
                )
            ),
            blocking_ambiguities=(
                blocking_count
            ),
            predicted_counts=(
                dry_run[
                    "predicted_counts"
                ]
            ),
            execution_ready=(
                execution_ready
            ),
        )

    def failure_route(
        self,
        category: str,
    ) -> str:
        category = _text(
            category,
            "category",
        ).lower()

        routes = {
            "highlight":
                rung_1_stages[23].stage_id,

            "material":
                rung_1_stages[20].stage_id,

            "lighting":
                rung_1_stages[22].stage_id,

            "curve":
                rung_1_stages[10].stage_id,

            "curvature":
                rung_1_stages[10].stage_id,

            "negative-space":
                rung_1_stages[11].stage_id,

            "negative space":
                rung_1_stages[11].stage_id,

            "topology":
                rung_1_stages[3].stage_id,

            "boolean":
                rung_1_stages[13].stage_id,

            "anchors":
                rung_1_stages[9].stage_id,

            "primitive":
                rung_1_stages[8].stage_id,

            "shadow":
                rung_1_stages[24].stage_id,

            "depth":
                rung_1_stages[25].stage_id,

            "mask":
                rung_1_stages[26].stage_id,

            "clipping":
                rung_1_stages[26].stage_id,

            "gradient":
                rung_1_stages[18].stage_id,

            "color":
                rung_1_stages[16].stage_id,

            "symmetry":
                rung_1_stages[6].stage_id,

            "occlusion":
                rung_1_stages[5].stage_id,

            "optical-size":
                rung_1_stages[29].stage_id,

            "optical size":
                rung_1_stages[29].stage_id,
        }

        if category in routes:
            return routes[category]

        return rung_1_stages[
            30
        ].stage_id

    def manifest(self) -> dict[str, Any]:
        graph = self.construction_graph()

        stage_results = [
            self._stage_results[
                key
            ].normalized()
            for key in sorted(
                self._stage_results
            )
        ]

        body = {
            "schema":
                schema,

            "name":
                name,

            "source_digest":
                self.source_digest,

            "stage_counts": {
                "understand":
                    len(rung_1_stages),

                "prove":
                    len(rung_2_stages),

                "construct":
                    len(rung_3_stages),

                "total":
                    len(all_stages),
            },

            "construction_digest":
                graph["digest"],

            "evidence_count":
                len(self._evidence),

            "ambiguity_count":
                len(self._ambiguities),

            "primitive_count":
                len(self._primitives),

            "segue_count":
                len(self._segues),

            "candidate_count":
                len(self._candidates),

            "stage_results":
                stage_results,

            "verification_lock":
                list(
                    verification_lock
                ),

            "failure_routing":
                "earliest-causal-stage",

            "truth_states": [
                "observed",
                "constrained",
                "inferred",
                "ambiguous",
                "authored",
            ],

            "representation_chain": [
                "raster-evidence",
                "inferred-construction",
                "semantic-vector-primitives",
                "material-system",
                "deterministic-projections",
            ],

            "instance_first":
                True,

            "typed_segues":
                True,

            "semantic_economy":
                True,

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,
        }

        body["digest"] = _digest(body)

        return body


def selftest() -> dict[str, Any]:
    pipeline = ReconstructionPipeline(
        "verification-source"
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

    upper_id = pipeline.substantiate(
        ConstructionPrimitive(
            primitive_id="upper-ribbon",
            kind="closed-cubic-bezier",
            parameters={
                "anchors":
                    6,
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

    lower_id = pipeline.substantiate(
        ConstructionPrimitive(
            primitive_id="lower-ribbon",
            kind="closed-cubic-bezier",
            parameters={
                "derived_from":
                    upper_id,
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

    segue_id = pipeline.relate(
        ConstructionSegue(
            kind="rotate180",
            source=upper_id,
            target=lower_id,
            parameters={
                "origin":
                    "center",
            },
            provenance=(
                "selftest",
            ),
        )
    )

    candidate_id = pipeline.add_candidate(
        Candidate(
            candidate_id="semantic-ribbons",
            strategy=(
                "three-ribbon-primitives-"
                "shared-material"
            ),
            primitive_ids=(
                upper_id,
                lower_id,
            ),
            segue_ids=(
                segue_id,
            ),
            predicted_cost={
                "paths": 2,
                "anchors": 12,
                "gradients": 2,
                "masks": 0,
                "clips": 0,
                "filters": 0,
            },
            predicted_quality={
                "fidelity": 0.95,
                "structural": 1.0,
                "editability": 1.0,
                "economy": 1.0,
                "compatibility": 1.0,
            },
            provenance=(
                "selftest",
            ),
        )
    )

    steps = (
        ExecutionStep(
            step_id="build-upper",
            stage_id=(
                rung_3_stages[
                    3
                ].stage_id
            ),
            operation=(
                "construct-primary-bezier"
            ),
            primitive_ids=(
                upper_id,
            ),
        ),
        ExecutionStep(
            step_id="derive-lower",
            stage_id=(
                rung_3_stages[
                    5
                ].stage_id
            ),
            operation=(
                "derive-symmetry-instance"
            ),
            primitive_ids=(
                lower_id,
            ),
            segue_ids=(
                segue_id,
            ),
            dependencies=(
                "build-upper",
            ),
        ),
    )

    contract_a = (
        pipeline
        .compile_execution_contract(
            candidate_id,
            steps,
        )
        .normalized()
    )

    contract_b = (
        pipeline
        .compile_execution_contract(
            candidate_id,
            steps,
        )
        .normalized()
    )

    graph_a = (
        pipeline.construction_graph()
    )

    graph_b = (
        pipeline.construction_graph()
    )

    plan_a = [
        item.normalized()
        for item in pipeline.opus_plan(
            1
        )
    ]

    plan_b = [
        item.normalized()
        for item in pipeline.opus_plan(
            1
        )
    ]

    checks = {
        "name_exact":
            name == "blot.",

        "authority_none":
            authority_effect == "none",

        "mutation_none":
            mutation_effect == "none",

        "projection_only":
            projection_only is True,

        "stage_total":
            len(all_stages) == 92,

        "rung_1":
            len(rung_1_stages) == 32,

        "rung_2":
            len(rung_2_stages) == 28,

        "rung_3":
            len(rung_3_stages) == 32,

        "substance_once":
            len(
                graph_a[
                    "primitives"
                ]
            )
            == 2,

        "typed_segue":
            len(
                graph_a[
                    "segues"
                ]
            )
            == 1,

        "candidate_present":
            len(
                pipeline._candidates
            )
            == 1,

        "hard_gate_ready":
            contract_a[
                "execution_ready"
            ]
            is True,

        "blocking_ambiguities_zero":
            contract_a[
                "blocking_ambiguities"
            ]
            == 0,

        "predicted_counts":
            contract_a[
                "predicted_counts"
            ][
                "paths"
            ]
            == 2,

        "deterministic_graph":
            graph_a == graph_b,

        "deterministic_contract":
            contract_a == contract_b,

        "deterministic_opus_plan":
            plan_a == plan_b,

        "opus_work_count":
            len(plan_a) == 32,

        "opus_execution_owner":
            all(
                item[
                    "execution_owner"
                ]
                == "opus"
                for item in plan_a
            ),

        "failure_route_curve":
            pipeline.failure_route(
                "curve"
            )
            == rung_1_stages[
                10
            ].stage_id,

        "verification_lock":
            len(
                verification_lock
            )
            == 20,
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

        "construction_digest":
            graph_a[
                "digest"
            ],

        "contract_digest":
            contract_a[
                "digest"
            ],

        "manifest":
            pipeline.manifest(),

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,
    }

    result["digest"] = _digest(result)

    return result


__all__ = [
    "Ambiguity",
    "BlotReconstructionError",
    "Candidate",
    "ConstructionPrimitive",
    "ConstructionSegue",
    "Evidence",
    "ExecutionContract",
    "ExecutionStep",
    "OpusWorkUnit",
    "ReconstructionPipeline",
    "Stage",
    "StageResult",
    "all_stages",
    "authority_effect",
    "max_ambiguities",
    "max_candidates",
    "max_dependencies",
    "max_evidence",
    "max_execution_steps",
    "max_primitives",
    "max_segues",
    "max_stage_attempts",
    "max_stage_results",
    "mutation_effect",
    "name",
    "projection_only",
    "rung_1_stages",
    "rung_2_stages",
    "rung_3_stages",
    "schema",
    "selftest",
    "verification_lock",
]


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
