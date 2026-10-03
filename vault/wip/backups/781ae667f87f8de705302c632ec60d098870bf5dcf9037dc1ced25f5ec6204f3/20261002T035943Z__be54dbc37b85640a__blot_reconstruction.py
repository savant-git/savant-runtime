#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


name = "blot."
schema = "savant.translucent.blot.reconstruction.v1"
authority_effect = "none"
projection_only = True

max_candidates = 16
max_stage_attempts = 3
max_dependencies = 256
max_evidence = 4096
max_primitives = 8192
max_ambiguities = 1024


class BlotReconstructionError(ValueError):
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
    return hashlib.sha256(
        _canonical(value).encode("utf-8")
    ).hexdigest()


def _text(value: Any, name: str) -> str:
    result = str(value).strip()

    if not result:
        raise BlotReconstructionError(
            f"{name} is required"
        )

    return result


def _confidence(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise BlotReconstructionError(
            "confidence must be numeric"
        ) from exc

    if not 0.0 <= result <= 1.0:
        raise BlotReconstructionError(
            "confidence must be between zero and one"
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


@dataclass(frozen=True, slots=True)
class Stage:
    stage_id: str
    rung: int
    order: int
    purpose: str
    owner: str
    capability: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    opus_orchestrated: bool = True
    deterministic: bool = True
    parallelizable: bool = False
    cacheable: bool = True

    def normalized(self) -> dict[str, Any]:
        if self.rung not in {1, 2, 3}:
            raise BlotReconstructionError(
                "stage rung must be 1, 2, or 3"
            )

        if self.order < 1:
            raise BlotReconstructionError(
                "stage order must be positive"
            )

        return {
            "stage_id":
                _text(
                    self.stage_id,
                    "stage_id",
                ),

            "rung":
                self.rung,

            "order":
                self.order,

            "purpose":
                _text(
                    self.purpose,
                    "purpose",
                ),

            "owner":
                _text(
                    self.owner,
                    "owner",
                ),

            "capability":
                _text(
                    self.capability,
                    "capability",
                ),

            "inputs":
                list(
                    _unique_text(
                        self.inputs
                    )
                ),

            "outputs":
                list(
                    _unique_text(
                        self.outputs
                    )
                ),

            "tools":
                list(
                    _unique_text(
                        self.tools
                    )
                ),

            "constraints":
                list(
                    _unique_text(
                        self.constraints
                    )
                ),

            "opus_orchestrated":
                bool(
                    self.opus_orchestrated
                ),

            "deterministic":
                bool(
                    self.deterministic
                ),

            "parallelizable":
                bool(
                    self.parallelizable
                ),

            "cacheable":
                bool(
                    self.cacheable
                ),
        }


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    kind: str
    payload: Mapping[str, Any]
    confidence: float = 1.0
    provenance: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        return {
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
                dict(
                    self.payload
                ),

            "confidence":
                _confidence(
                    self.confidence
                ),

            "provenance":
                list(
                    _unique_text(
                        self.provenance
                    )
                ),

            "lineage":
                list(
                    _unique_text(
                        self.lineage
                    )
                ),
        }


@dataclass(frozen=True, slots=True)
class Ambiguity:
    ambiguity_id: str
    subject: str
    alternatives: tuple[str, ...]
    evidence_ids: tuple[str, ...] = ()
    blocking: bool = False
    confidence: float = 0.5

    def normalized(self) -> dict[str, Any]:
        alternatives = _unique_text(
            self.alternatives
        )

        if len(alternatives) < 2:
            raise BlotReconstructionError(
                "ambiguity requires at least two alternatives"
            )

        return {
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

            "alternatives":
                list(
                    alternatives
                ),

            "evidence_ids":
                list(
                    _unique_text(
                        self.evidence_ids
                    )
                ),

            "blocking":
                bool(
                    self.blocking
                ),

            "confidence":
                _confidence(
                    self.confidence
                ),
        }


@dataclass(frozen=True, slots=True)
class ConstructionPrimitive:
    primitive_id: str
    kind: str
    parameters: Mapping[str, Any]
    evidence_ids: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    relationships: tuple[str, ...] = ()
    confidence: float = 1.0
    provenance: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        dependencies = _unique_text(
            self.dependencies
        )

        if len(dependencies) > max_dependencies:
            raise BlotReconstructionError(
                "primitive dependency limit exceeded"
            )

        return {
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
                dict(
                    self.parameters
                ),

            "evidence_ids":
                list(
                    _unique_text(
                        self.evidence_ids
                    )
                ),

            "dependencies":
                list(
                    dependencies
                ),

            "relationships":
                list(
                    _unique_text(
                        self.relationships
                    )
                ),

            "confidence":
                _confidence(
                    self.confidence
                ),

            "provenance":
                list(
                    _unique_text(
                        self.provenance
                    )
                ),

            "lineage":
                list(
                    _unique_text(
                        self.lineage
                    )
                ),
        }


@dataclass(frozen=True, slots=True)
class Candidate:
    candidate_id: str
    strategy: str
    primitive_ids: tuple[str, ...]
    predicted_cost: Mapping[str, Any]
    predicted_quality: Mapping[str, Any]
    risks: tuple[str, ...] = ()
    rejected: bool = False
    rejection_reasons: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        return {
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

            "predicted_cost":
                dict(
                    self.predicted_cost
                ),

            "predicted_quality":
                dict(
                    self.predicted_quality
                ),

            "risks":
                list(
                    _unique_text(
                        self.risks
                    )
                ),

            "rejected":
                bool(
                    self.rejected
                ),

            "rejection_reasons":
                list(
                    _unique_text(
                        self.rejection_reasons
                    )
                ),
        }


@dataclass(frozen=True, slots=True)
class OpusWorkUnit:
    work_id: str
    stage_id: str
    capability: str
    inputs: Mapping[str, Any]
    dependencies: tuple[str, ...] = ()
    preferred_providers: tuple[str, ...] = ()
    candidate_budget: int = 1
    deterministic: bool = True
    native_fallback: bool = True

    def normalized(self) -> dict[str, Any]:
        budget = int(
            self.candidate_budget
        )

        if not 1 <= budget <= max_candidates:
            raise BlotReconstructionError(
                "candidate budget outside allowed range"
            )

        dependencies = _unique_text(
            self.dependencies
        )

        if len(dependencies) > max_dependencies:
            raise BlotReconstructionError(
                "work dependency limit exceeded"
            )

        return {
            "schema":
                "savant.opus.work-unit.v1",

            "owner":
                "opus",

            "requester":
                "blot.",

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

            "inputs":
                dict(
                    self.inputs
                ),

            "dependencies":
                list(
                    dependencies
                ),

            "preferred_providers":
                list(
                    _unique_text(
                        self.preferred_providers
                    )
                ),

            "candidate_budget":
                budget,

            "deterministic":
                bool(
                    self.deterministic
                ),

            "native_fallback":
                bool(
                    self.native_fallback
                ),

            "execution_owner":
                "opus",

            "routing_owner":
                "opus",

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    step_id: str
    stage_id: str
    operation: str
    primitive_ids: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    parameters: Mapping[str, Any] = field(
        default_factory=dict
    )

    def normalized(self) -> dict[str, Any]:
        return {
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

            "dependencies":
                list(
                    _unique_text(
                        self.dependencies
                    )
                ),

            "parameters":
                dict(
                    self.parameters
                ),
        }


@dataclass(frozen=True, slots=True)
class ExecutionContract:
    contract_id: str
    source_digest: str
    construction_digest: str
    candidate_id: str
    steps: tuple[ExecutionStep, ...]
    blocking_ambiguities: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()

    @property
    def execution_ready(self) -> bool:
        return not self.blocking_ambiguities

    def normalized(self) -> dict[str, Any]:
        result = {
            "schema":
                f"{schema}.execution-contract",

            "contract_id":
                _text(
                    self.contract_id,
                    "contract_id",
                ),

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

            "candidate_id":
                _text(
                    self.candidate_id,
                    "candidate_id",
                ),

            "steps":
                [
                    step.normalized()
                    for step in self.steps
                ],

            "blocking_ambiguities":
                list(
                    _unique_text(
                        self.blocking_ambiguities
                    )
                ),

            "execution_ready":
                self.execution_ready,

            "provenance":
                list(
                    _unique_text(
                        self.provenance
                    )
                ),

            "lineage":
                list(
                    _unique_text(
                        self.lineage
                    )
                ),

            "authority_effect":
                "none",

            "projection_only":
                True,
        }

        result["digest"] = _digest(
            result
        )

        return result


def _stage(
    rung: int,
    order: int,
    stage_id: str,
    purpose: str,
    capability: str,
    *,
    tools: Sequence[str] = (),
    inputs: Sequence[str] = (),
    outputs: Sequence[str] = (),
    constraints: Sequence[str] = (),
    owner: str = "blot.",
    parallelizable: bool = False,
    deterministic: bool = True,
) -> Stage:
    return Stage(
        stage_id=stage_id,
        rung=rung,
        order=order,
        purpose=purpose,
        owner=owner,
        capability=capability,
        inputs=tuple(inputs),
        outputs=tuple(outputs),
        tools=tuple(tools),
        constraints=tuple(constraints),
        opus_orchestrated=True,
        deterministic=deterministic,
        parallelizable=parallelizable,
        cacheable=True,
    )


rung_1 = (
    _stage(1, 1, "source-normalization", "normalize immutable raster evidence", "vision.source-normalization", tools=("color-management", "alpha-analysis")),
    _stage(1, 2, "artifact-assessment", "separate raster defects from authored structure", "vision.artifact-analysis", tools=("sampling-analysis", "compression-analysis")),
    _stage(1, 3, "visual-hierarchy", "decompose primary and secondary visual hierarchy", "vision.semantic-decomposition"),
    _stage(1, 4, "topology-inference", "infer objects holes islands intersections and containment", "geometry.topology"),
    _stage(1, 5, "semantic-segmentation", "separate designed objects from appearance changes", "vision.semantic-segmentation"),
    _stage(1, 6, "occlusion-analysis", "infer front back and hidden continuation relationships", "vision.occlusion"),
    _stage(1, 7, "symmetry-analysis", "detect exact and approximate geometric symmetries", "geometry.symmetry"),
    _stage(1, 8, "scaffold-recovery", "recover axes grids radii proportions alignments and construction guides", "geometry.scaffold"),
    _stage(1, 9, "primitive-classification", "choose semantically appropriate vector primitives", "geometry.primitive-selection"),
    _stage(1, 10, "curve-planning", "infer sparse cubic bezier structure", "geometry.bezier-analysis", tools=("pen-tool", "cubic-bezier")),
    _stage(1, 11, "curvature-analysis", "infer corners extrema inflections tangencies and continuity", "geometry.curvature"),
    _stage(1, 12, "negative-space", "reconstruct negative space as designed geometry", "geometry.negative-space"),
    _stage(1, 13, "stroke-fill-inference", "distinguish strokes fills bevels shadows and light edges", "geometry.stroke-fill"),
    _stage(1, 14, "boolean-analysis", "infer unions differences intersections exclusions and compounds", "geometry.boolean", tools=("union", "difference", "intersection", "exclusion")),
    _stage(1, 15, "canonical-geometry", "define material-independent canonical geometry", "geometry.canonicalization"),
    _stage(1, 16, "shape-economy", "minimize primitives without losing semantics or fidelity", "geometry.economy"),
    _stage(1, 17, "base-color", "recover intrinsic colors independently of illumination", "appearance.base-color"),
    _stage(1, 18, "palette-relations", "recover palette roles contrast and perceptual relationships", "appearance.palette"),
    _stage(1, 19, "gradient-field", "infer gradient topology direction focal behavior and stops", "appearance.gradient-analysis"),
    _stage(1, 20, "gradient-planning", "map inferred fields to reusable vector gradients", "appearance.gradient-construction", tools=("linear-gradient", "radial-gradient", "gradient-transform")),
    _stage(1, 21, "material-inference", "infer material response rather than pixel texture", "appearance.material"),
    _stage(1, 22, "surface-orientation", "infer surface orientation needed for coherent shading", "appearance.surface-orientation"),
    _stage(1, 23, "lighting-decomposition", "separate ambient key fill rim emissive and reflected light", "appearance.lighting"),
    _stage(1, 24, "highlight-analysis", "infer broad and sharp specular structures", "appearance.highlight"),
    _stage(1, 25, "shadow-analysis", "distinguish cast contact self shadow and occlusion", "appearance.shadow"),
    _stage(1, 26, "depth-analysis", "infer bevel extrusion inset and dimensional treatment", "appearance.depth"),
    _stage(1, 27, "mask-clip-analysis", "select hard clipping versus soft masking semantics", "composition.mask-clip", tools=("clip-path", "mask")),
    _stage(1, 28, "texture-abstraction", "retain only identity-bearing texture", "appearance.texture"),
    _stage(1, 29, "tool-selection", "select the cheapest correct vector tool for each feature", "vector.tool-selection", tools=("path", "stroke", "compound-path", "boolean", "gradient", "pattern", "clip-path", "mask", "filter", "symbol", "use", "transform")),
    _stage(1, 30, "optical-projection", "plan presentation standard micro flat and monochrome projections", "projection.optical-size"),
    _stage(1, 31, "perceptual-specification", "define measurable reconstruction fidelity targets", "verification.perceptual"),
    _stage(1, 32, "structural-specification", "define editability economy and structural quality targets", "verification.structural"),
)


rung_2 = (
    _stage(2, 1, "graph-integrity", "verify construction graph integrity", "simulation.graph-integrity"),
    _stage(2, 2, "ambiguity-inventory", "enumerate unresolved construction alternatives", "simulation.ambiguity"),
    _stage(2, 3, "confidence-propagation", "propagate evidence confidence through dependencies", "simulation.confidence"),
    _stage(2, 4, "tool-feasibility", "prove planned operations are representable", "simulation.tool-feasibility"),
    _stage(2, 5, "renderer-compatibility", "predict renderer and editor compatibility", "simulation.renderer"),
    _stage(2, 6, "primitive-rehearsal", "virtually instantiate planned primitives", "simulation.primitive"),
    _stage(2, 7, "anchor-rehearsal", "simulate bezier anchor and handle placement", "simulation.bezier"),
    _stage(2, 8, "continuity-rehearsal", "verify g0 g1 and g2 continuity requirements", "simulation.continuity"),
    _stage(2, 9, "boolean-rehearsal", "simulate constructive boolean operations", "simulation.boolean"),
    _stage(2, 10, "compound-rehearsal", "simulate compound paths and winding behavior", "simulation.compound-path"),
    _stage(2, 11, "transform-rehearsal", "verify reusable transformed instances", "simulation.transform"),
    _stage(2, 12, "negative-space-verification", "verify negative-space geometry", "simulation.negative-space"),
    _stage(2, 13, "self-intersection", "predict invalid self intersections", "simulation.self-intersection"),
    _stage(2, 14, "winding-verification", "verify fill rules and winding", "simulation.winding"),
    _stage(2, 15, "degeneracy-detection", "reject degenerate geometry before execution", "simulation.degeneracy"),
    _stage(2, 16, "material-simulation", "simulate material response", "simulation.material", parallelizable=True),
    _stage(2, 17, "lighting-simulation", "simulate lighting relationships", "simulation.lighting", parallelizable=True),
    _stage(2, 18, "gradient-simulation", "simulate gradient fields and transforms", "simulation.gradient", parallelizable=True),
    _stage(2, 19, "highlight-simulation", "simulate specular placement", "simulation.highlight", parallelizable=True),
    _stage(2, 20, "shadow-simulation", "simulate shadow projection", "simulation.shadow", parallelizable=True),
    _stage(2, 21, "mask-simulation", "simulate mask interactions", "simulation.mask", parallelizable=True),
    _stage(2, 22, "clip-simulation", "simulate clipping interactions", "simulation.clip", parallelizable=True),
    _stage(2, 23, "compositing-simulation", "simulate transparency and compositing", "simulation.compositing"),
    _stage(2, 24, "stroke-simulation", "simulate stroke expansion and joins", "simulation.stroke"),
    _stage(2, 25, "complexity-forecast", "predict paths anchors masks filters and output size", "simulation.complexity"),
    _stage(2, 26, "redundancy-forecast", "detect duplicate substance and unnecessary geometry", "simulation.redundancy"),
    _stage(2, 27, "failure-prediction", "predict likely structural and perceptual failures", "simulation.failure"),
    _stage(2, 28, "execution-compilation", "compile one deterministic execution contract", "simulation.execution-contract"),
)


rung_3 = (
    _stage(3, 1, "document-initialize", "initialize projection coordinate system", "execution.document"),
    _stage(3, 2, "scaffold-build", "instantiate geometric scaffold", "execution.scaffold"),
    _stage(3, 3, "centerline-build", "construct canonical centerlines", "execution.centerline"),
    _stage(3, 4, "bezier-build", "construct sparse cubic bezier silhouettes", "execution.bezier", tools=("pen-tool", "cubic-bezier")),
    _stage(3, 5, "constraint-enforcement", "enforce geometric and continuity constraints", "execution.constraints"),
    _stage(3, 6, "symmetry-instances", "instantiate symmetry-derived geometry", "execution.instances"),
    _stage(3, 7, "negative-space-build", "construct intentional negative spaces", "execution.negative-space"),
    _stage(3, 8, "compound-build", "construct compound paths", "execution.compound-path"),
    _stage(3, 9, "boolean-execution", "execute constructive booleans", "execution.boolean"),
    _stage(3, 10, "secondary-geometry", "construct inset bevel and secondary geometry", "execution.secondary-geometry"),
    _stage(3, 11, "stroke-build", "construct true stroke semantics", "execution.stroke"),
    _stage(3, 12, "topology-normalize", "normalize winding topology and containment", "execution.topology"),
    _stage(3, 13, "palette-build", "instantiate canonical palette tokens", "execution.palette"),
    _stage(3, 14, "material-build", "instantiate reusable material definitions", "execution.material"),
    _stage(3, 15, "base-fill-build", "apply intrinsic base fills", "execution.fill"),
    _stage(3, 16, "linear-gradient-build", "construct linear gradients", "execution.linear-gradient"),
    _stage(3, 17, "radial-gradient-build", "construct radial and focal gradients", "execution.radial-gradient"),
    _stage(3, 18, "gradient-transform-build", "apply surface-aware gradient transforms", "execution.gradient-transform"),
    _stage(3, 19, "material-overlay-build", "construct justified material overlays", "execution.material-overlay"),
    _stage(3, 20, "key-light-build", "construct key-light response", "execution.key-light"),
    _stage(3, 21, "fill-light-build", "construct fill-light response", "execution.fill-light"),
    _stage(3, 22, "specular-build", "construct specular highlights", "execution.specular"),
    _stage(3, 23, "rim-light-build", "construct rim-light response", "execution.rim-light"),
    _stage(3, 24, "self-shadow-build", "construct self-shadow response", "execution.self-shadow"),
    _stage(3, 25, "cast-shadow-build", "construct cast and contact shadows", "execution.cast-shadow"),
    _stage(3, 26, "depth-build", "construct bevel and dimensional treatment", "execution.depth"),
    _stage(3, 27, "clip-build", "construct hard clipping paths", "execution.clip"),
    _stage(3, 28, "mask-build", "construct soft masks", "execution.mask"),
    _stage(3, 29, "effect-build", "construct only justified scalable effects", "execution.effect"),
    _stage(3, 30, "composite-build", "establish deterministic compositing order", "execution.composite"),
    _stage(3, 31, "master-projection", "project canonical presentation vector", "projection.vector-master"),
    _stage(3, 32, "derived-projections", "derive flat monochrome standard and micro projections", "projection.derived"),
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
    "materials",
    "lighting",
    "masks",
    "clipping",
    "optical-size",
    "editability",
    "primitive-count",
    "anchor-economy",
    "renderer-stability",
    "deterministic-replay",
    "lineage",
    "provenance",
)


all_stages = (
    rung_1
    + rung_2
    + rung_3
)


class ReconstructionPipeline:
    def __init__(
        self,
        *,
        source_digest: str,
        preferred_providers: Iterable[str] = (),
    ) -> None:
        self.source_digest = _text(
            source_digest,
            "source_digest",
        )

        self.preferred_providers = _unique_text(
            preferred_providers
        )

        self._evidence: dict[str, Evidence] = {}
        self._ambiguities: dict[str, Ambiguity] = {}
        self._primitives: dict[
            str,
            ConstructionPrimitive,
        ] = {}
        self._candidates: dict[str, Candidate] = {}

    def add_evidence(
        self,
        evidence: Evidence,
    ) -> str:
        if len(self._evidence) >= max_evidence:
            raise BlotReconstructionError(
                "evidence limit exceeded"
            )

        normalized = evidence.normalized()
        evidence_id = normalized["evidence_id"]

        existing = self._evidence.get(
            evidence_id
        )

        if (
            existing is not None
            and existing.normalized()
            != normalized
        ):
            raise BlotReconstructionError(
                f"conflicting evidence id: {evidence_id}"
            )

        self._evidence[evidence_id] = evidence

        return evidence_id

    def add_ambiguity(
        self,
        ambiguity: Ambiguity,
    ) -> str:
        if len(self._ambiguities) >= max_ambiguities:
            raise BlotReconstructionError(
                "ambiguity limit exceeded"
            )

        normalized = ambiguity.normalized()
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
                f"conflicting ambiguity id: {ambiguity_id}"
            )

        self._ambiguities[
            ambiguity_id
        ] = ambiguity

        return ambiguity_id

    def substantiate(
        self,
        primitive: ConstructionPrimitive,
    ) -> str:
        if len(self._primitives) >= max_primitives:
            raise BlotReconstructionError(
                "primitive limit exceeded"
            )

        normalized = primitive.normalized()
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
                f"conflicting primitive id: {primitive_id}"
            )

        for evidence_id in normalized[
            "evidence_ids"
        ]:
            if evidence_id not in self._evidence:
                raise BlotReconstructionError(
                    "primitive references unknown evidence: "
                    f"{evidence_id}"
                )

        self._primitives[
            primitive_id
        ] = primitive

        return primitive_id

    def add_candidate(
        self,
        candidate: Candidate,
    ) -> str:
        if len(self._candidates) >= max_candidates:
            raise BlotReconstructionError(
                "candidate limit exceeded"
            )

        normalized = candidate.normalized()
        candidate_id = normalized[
            "candidate_id"
        ]

        for primitive_id in normalized[
            "primitive_ids"
        ]:
            if primitive_id not in self._primitives:
                raise BlotReconstructionError(
                    "candidate references unknown primitive: "
                    f"{primitive_id}"
                )

        self._candidates[
            candidate_id
        ] = candidate

        return candidate_id

    def construction_graph(
        self,
    ) -> dict[str, Any]:
        result = {
            "schema":
                f"{schema}.construction-graph",

            "source_digest":
                self.source_digest,

            "evidence":
                [
                    self._evidence[key].normalized()
                    for key in sorted(
                        self._evidence
                    )
                ],

            "ambiguities":
                [
                    self._ambiguities[key].normalized()
                    for key in sorted(
                        self._ambiguities
                    )
                ],

            "primitives":
                [
                    self._primitives[key].normalized()
                    for key in sorted(
                        self._primitives
                    )
                ],

            "authority_effect":
                "none",

            "projection_only":
                True,
        }

        result["digest"] = _digest(
            result
        )

        return result

    def opus_plan(
        self,
        rung: int,
    ) -> tuple[OpusWorkUnit, ...]:
        if rung not in {1, 2, 3}:
            raise BlotReconstructionError(
                "rung must be 1, 2, or 3"
            )

        graph = self.construction_graph()

        units: list[OpusWorkUnit] = []
        previous: str | None = None

        for stage in all_stages:
            if stage.rung != rung:
                continue

            work_id = (
                f"blot-opus-"
                f"{rung:01d}-"
                f"{stage.order:02d}-"
                f"{_digest((self.source_digest, stage.stage_id))[:16]}"
            )

            dependencies = (
                (previous,)
                if (
                    previous is not None
                    and not stage.parallelizable
                )
                else ()
            )

            units.append(
                OpusWorkUnit(
                    work_id=work_id,
                    stage_id=stage.stage_id,
                    capability=stage.capability,
                    inputs={
                        "source_digest":
                            self.source_digest,

                        "construction_digest":
                            graph["digest"],

                        "stage":
                            stage.normalized(),
                    },
                    dependencies=dependencies,
                    preferred_providers=self.preferred_providers,
                    candidate_budget=(
                        min(
                            4,
                            max_candidates,
                        )
                        if stage.parallelizable
                        else 1
                    ),
                    deterministic=stage.deterministic,
                    native_fallback=True,
                )
            )

            if not stage.parallelizable:
                previous = work_id

        return tuple(
            units
        )

    def opus_packet(
        self,
        rung: int,
    ) -> dict[str, Any]:
        units = self.opus_plan(
            rung
        )

        result = {
            "schema":
                "savant.opus.orchestration-packet.v1",

            "owner":
                "opus",

            "requester":
                "blot.",

            "rung":
                rung,

            "source_digest":
                self.source_digest,

            "work_units":
                [
                    unit.normalized()
                    for unit in units
                ],

            "execution_owner":
                "opus",

            "routing_owner":
                "opus",

            "provider_neutral":
                True,

            "bounded_parallelism":
                True,

            "native_fallback":
                True,

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }

        result["digest"] = _digest(
            result
        )

        return result

    def dry_run(
        self,
    ) -> dict[str, Any]:
        graph = self.construction_graph()

        candidates = [
            self._candidates[key].normalized()
            for key in sorted(
                self._candidates
            )
        ]

        viable = [
            candidate
            for candidate in candidates
            if not candidate["rejected"]
        ]

        blocking = [
            ambiguity["ambiguity_id"]
            for ambiguity in (
                item.normalized()
                for item in self._ambiguities.values()
            )
            if ambiguity["blocking"]
        ]

        result = {
            "schema":
                f"{schema}.dry-run",

            "source_digest":
                self.source_digest,

            "construction_digest":
                graph["digest"],

            "candidate_count":
                len(candidates),

            "viable_candidate_count":
                len(viable),

            "candidates":
                candidates,

            "blocking_ambiguities":
                sorted(
                    blocking
                ),

            "execution_ready":
                bool(viable)
                and not blocking,

            "complexity":
                {
                    "evidence":
                        len(
                            self._evidence
                        ),

                    "ambiguities":
                        len(
                            self._ambiguities
                        ),

                    "primitives":
                        len(
                            self._primitives
                        ),

                    "candidates":
                        len(
                            self._candidates
                        ),
                },

            "opus":
                self.opus_packet(
                    2
                ),

            "authority_effect":
                "none",

            "projection_only":
                True,
        }

        result["digest"] = _digest(
            result
        )

        return result

    def compile_execution_contract(
        self,
        candidate_id: str,
        steps: Sequence[ExecutionStep],
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

        if candidate.rejected:
            raise BlotReconstructionError(
                "cannot compile a rejected candidate"
            )

        blocking = tuple(
            sorted(
                ambiguity.ambiguity_id
                for ambiguity
                in self._ambiguities.values()
                if ambiguity.blocking
            )
        )

        graph = self.construction_graph()

        substance = {
            "source_digest":
                self.source_digest,

            "construction_digest":
                graph["digest"],

            "candidate_id":
                candidate_id,

            "steps":
                [
                    step.normalized()
                    for step in steps
                ],

            "blocking_ambiguities":
                list(
                    blocking
                ),
        }

        contract_id = (
            "blot-contract-"
            + _digest(
                substance
            )[:24]
        )

        return ExecutionContract(
            contract_id=contract_id,
            source_digest=self.source_digest,
            construction_digest=graph["digest"],
            candidate_id=candidate_id,
            steps=tuple(steps),
            blocking_ambiguities=blocking,
            provenance=(
                f"source:{self.source_digest}",
                "orchestrator:opus",
                "constructor:blot.",
            ),
            lineage=(
                graph["digest"],
            ),
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        result = {
            "schema":
                f"{schema}.manifest",

            "name":
                name,

            "authority_effect":
                authority_effect,

            "projection_only":
                projection_only,

            "orchestration_owner":
                "opus",

            "construction_owner":
                "blot.",

            "rungs":
                {
                    "1":
                        [
                            stage.normalized()
                            for stage in rung_1
                        ],

                    "2":
                        [
                            stage.normalized()
                            for stage in rung_2
                        ],

                    "3":
                        [
                            stage.normalized()
                            for stage in rung_3
                        ],
                },

            "stage_count":
                len(
                    all_stages
                ),

            "verification_lock":
                list(
                    verification_lock
                ),

            "architecture":
                {
                    "substantiate_once":
                        True,

                    "instances_over_copies":
                        True,

                    "typed_segues":
                        True,

                    "deterministic_projection":
                        True,

                    "immutable_evidence":
                        True,

                    "explicit_ambiguity":
                        True,

                    "lineage_preserved":
                        True,

                    "provenance_preserved":
                        True,

                    "provider_neutral":
                        True,

                    "bounded_candidates":
                        True,

                    "bounded_parallelism":
                        True,

                    "replayable":
                        True,

                    "derived_state_rebuildable":
                        True,

                    "svg_is_projection":
                        True,

                    "dense_trace_is_non_authoritative":
                        True,
                },
        }

        result["digest"] = _digest(
            result
        )

        return result


def selftest() -> dict[str, Any]:
    pipeline = ReconstructionPipeline(
        source_digest="source-test",
        preferred_providers=(
            "provider-a",
            "provider-b",
        ),
    )

    evidence_id = pipeline.add_evidence(
        Evidence(
            evidence_id="evidence-geometry-1",
            kind="silhouette",
            payload={
                "region": "primary",
            },
            provenance=(
                "source:test",
            ),
        )
    )

    primitive_id = pipeline.substantiate(
        ConstructionPrimitive(
            primitive_id="primitive-ribbon-1",
            kind="cubic-bezier-shape",
            parameters={
                "anchors": 8,
                "continuity": "g2",
            },
            evidence_ids=(
                evidence_id,
            ),
            provenance=(
                "source:test",
            ),
        )
    )

    candidate_id = pipeline.add_candidate(
        Candidate(
            candidate_id="candidate-1",
            strategy="sparse-bezier",
            primitive_ids=(
                primitive_id,
            ),
            predicted_cost={
                "anchors": 8,
                "paths": 1,
            },
            predicted_quality={
                "structural": 1.0,
                "editability": 1.0,
            },
        )
    )

    dry_run = pipeline.dry_run()

    contract = pipeline.compile_execution_contract(
        candidate_id,
        (
            ExecutionStep(
                step_id="step-1",
                stage_id="bezier-build",
                operation="construct-cubic-bezier",
                primitive_ids=(
                    primitive_id,
                ),
            ),
        ),
    ).normalized()

    manifest = pipeline.manifest()

    checks = {
        "name_exact":
            manifest["name"]
            == "blot.",

        "authority_none":
            manifest["authority_effect"]
            == "none",

        "projection_only":
            manifest["projection_only"]
            is True,

        "opus_owner":
            manifest["orchestration_owner"]
            == "opus",

        "blot_owner":
            manifest["construction_owner"]
            == "blot.",

        "three_rungs":
            set(
                manifest["rungs"]
            )
            == {
                "1",
                "2",
                "3",
            },

        "stage_count":
            manifest["stage_count"]
            == 92,

        "dry_run_ready":
            dry_run["execution_ready"]
            is True,

        "contract_ready":
            contract["execution_ready"]
            is True,

        "provider_neutral":
            dry_run["opus"]["provider_neutral"]
            is True,

        "deterministic_manifest":
            manifest
            == pipeline.manifest(),

        "deterministic_graph":
            pipeline.construction_graph()
            == pipeline.construction_graph(),
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

        "manifest_digest":
            manifest["digest"],

        "construction_digest":
            pipeline.construction_graph()[
                "digest"
            ],

        "dry_run_digest":
            dry_run["digest"],

        "contract_digest":
            contract["digest"],
    }


__all__ = [
    "Ambiguity",
    "BlotReconstructionError",
    "Candidate",
    "ConstructionPrimitive",
    "Evidence",
    "ExecutionContract",
    "ExecutionStep",
    "OpusWorkUnit",
    "ReconstructionPipeline",
    "Stage",
    "all_stages",
    "authority_effect",
    "max_candidates",
    "name",
    "projection_only",
    "rung_1",
    "rung_2",
    "rung_3",
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
