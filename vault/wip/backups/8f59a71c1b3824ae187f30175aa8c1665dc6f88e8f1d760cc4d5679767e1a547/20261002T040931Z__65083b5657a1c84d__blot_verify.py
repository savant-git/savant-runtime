#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping


name = "blot."
schema = "savant.translucent.blot.verify.v1"
authority_effect = "none"
mutation_effect = "none"
projection_only = True


class BlotVerificationError(RuntimeError):
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


def _text(
    value: Any,
    field: str,
) -> str:
    result = str(value or "").strip()

    if not result:
        raise BlotVerificationError(
            f"{field} is required"
        )

    return result


def _mapping(
    value: Any,
    field: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BlotVerificationError(
            f"{field} must be a mapping"
        )

    return value


@dataclass(frozen=True, slots=True)
class VerificationCheck:
    check_id: str
    ok: bool
    category: str
    detail: str
    digest: str | None = None

    def normalized(self) -> dict[str, Any]:
        return {
            "check_id":
                _text(
                    self.check_id,
                    "check_id",
                ),

            "ok":
                bool(
                    self.ok
                ),

            "category":
                _text(
                    self.category,
                    "category",
                ),

            "detail":
                str(
                    self.detail
                ),

            "digest":
                self.digest,
        }


@dataclass(frozen=True, slots=True)
class VerificationReport:
    checks: tuple[
        VerificationCheck,
        ...
    ]

    def normalized(self) -> dict[str, Any]:
        checks = [
            check.normalized()
            for check in self.checks
        ]

        result = {
            "schema":
                schema,

            "name":
                name,

            "ok":
                all(
                    check[
                        "ok"
                    ]
                    for check in checks
                ),

            "check_count":
                len(
                    checks
                ),

            "passed":
                sum(
                    1
                    for check in checks
                    if check[
                        "ok"
                    ]
                ),

            "failed":
                sum(
                    1
                    for check in checks
                    if not check[
                        "ok"
                    ]
                ),

            "checks":
                checks,

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,
        }

        result[
            "digest"
        ] = _digest(
            result
        )

        return result


def _run_selftest(
    module_name: str,
    *,
    factory: Callable[
        [Any],
        tuple[
            tuple[Any, ...],
            dict[str, Any],
        ],
    ] | None = None,
) -> VerificationCheck:
    try:
        module = importlib.import_module(
            module_name
        )

        selftest = getattr(
            module,
            "selftest",
            None,
        )

        if not callable(
            selftest
        ):
            return VerificationCheck(
                check_id=(
                    "selftest:"
                    + module_name
                ),
                ok=False,
                category="selftest",
                detail=(
                    "module does not expose "
                    "a callable selftest"
                ),
            )

        if factory is None:
            args: tuple[Any, ...] = ()
            kwargs: dict[str, Any] = {}
        else:
            args, kwargs = factory(
                module
            )

        result = selftest(
            *args,
            **kwargs,
        )

        result = _mapping(
            result,
            f"{module_name}.selftest",
        )

        ok = result.get(
            "ok"
        ) is True

        return VerificationCheck(
            check_id=(
                "selftest:"
                + module_name
            ),
            ok=ok,
            category="selftest",
            detail=(
                "passed"
                if ok
                else _canonical(
                    result.get(
                        "checks",
                        result,
                    )
                )
            ),
            digest=_digest(
                result
            ),
        )

    except Exception as exc:
        return VerificationCheck(
            check_id=(
                "selftest:"
                + module_name
            ),
            ok=False,
            category="selftest",
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def _svg_runtime_factory(
    module: Any,
) -> tuple[
    tuple[Any, ...],
    dict[str, Any],
]:
    runtime_module = importlib.import_module(
        "runtime.translucent.svg.runtime"
    )

    runtime_type = getattr(
        runtime_module,
        "TranslucentSVGRuntime",
    )

    runtime = runtime_type()

    return (
        (
            runtime,
        ),
        {},
    )


def _check_core_compatibility(
) -> VerificationCheck:
    try:
        blot = importlib.import_module(
            "runtime.translucent.blot"
        )

        required = (
            "Blot",
            "BlotError",
            "GeometryInstance",
            "GeometrySegue",
            "GeometryShard",
            "Paint",
            "Transform",
            "circle",
            "ellipse",
            "path",
            "polygon",
            "rect",
            "star",
            "superellipse",
            "superformula",
        )

        missing = [
            item
            for item in required
            if not hasattr(
                blot,
                item,
            )
        ]

        if missing:
            return VerificationCheck(
                check_id=(
                    "core-public-compatibility"
                ),
                ok=False,
                category="compatibility",
                detail=(
                    "missing public symbols: "
                    + ", ".join(
                        missing
                    )
                ),
            )

        instance = blot.Blot(
            width=256,
            height=256,
        )

        shard = blot.circle(
            24
        )

        shard_id = instance.substantiate(
            shard
        )

        first_id = instance.instance(
            shard_id,
            transform=blot.Transform(
                x=-32,
            ),
            paint=blot.Paint(
                fill="#d9b44a",
                stroke="#11151a",
                stroke_width=2,
            ),
        )

        second_id = instance.instance(
            shard_id,
            transform=blot.Transform(
                x=32,
            ),
            paint=blot.Paint(
                fill="#d9b44a",
                stroke="#11151a",
                stroke_width=2,
            ),
        )

        instance.relate(
            "pair",
            first_id,
            second_id,
        )

        first_svg = instance.render()
        second_svg = instance.render()

        manifest_a = instance.manifest()
        manifest_b = instance.manifest()

        ok = (
            first_svg
            == second_svg
            and manifest_a
            == manifest_b
            and manifest_a.get(
                "authority_effect"
            )
            == "none"
            and manifest_a.get(
                "projection_only"
            )
            is True
            and manifest_a.get(
                "authoritative"
            )
            is False
            and len(
                manifest_a.get(
                    "shards",
                    [],
                )
            )
            == 1
            and len(
                manifest_a.get(
                    "instances",
                    [],
                )
            )
            == 2
            and len(
                manifest_a.get(
                    "segues",
                    [],
                )
            )
            == 1
        )

        return VerificationCheck(
            check_id=(
                "core-public-compatibility"
            ),
            ok=ok,
            category="compatibility",
            detail=(
                "passed"
                if ok
                else "core compatibility invariant failed"
            ),
            digest=_digest(
                {
                    "manifest":
                        manifest_a,

                    "svg":
                        first_svg,
                }
            ),
        )

    except Exception as exc:
        return VerificationCheck(
            check_id=(
                "core-public-compatibility"
            ),
            ok=False,
            category="compatibility",
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def _check_reconstruction_entrypoints(
) -> VerificationCheck:
    try:
        blot = importlib.import_module(
            "runtime.translucent.blot"
        )

        required = (
            "reconstruction_manifest",
            "reconstruction_pipeline",
            "reconstruction_runtime",
        )

        missing = [
            item
            for item in required
            if not callable(
                getattr(
                    blot,
                    item,
                    None,
                )
            )
        ]

        if missing:
            return VerificationCheck(
                check_id=(
                    "reconstruction-entrypoints"
                ),
                ok=False,
                category="integration",
                detail=(
                    "missing reconstruction entrypoints: "
                    + ", ".join(
                        missing
                    )
                ),
            )

        manifest_a = (
            blot.reconstruction_manifest()
        )

        manifest_b = (
            blot.reconstruction_manifest()
        )

        pipeline_a = (
            blot.reconstruction_pipeline(
                "verification-source"
            )
        )

        pipeline_b = (
            blot.reconstruction_pipeline(
                "verification-source"
            )
        )

        pipeline_manifest_a = (
            pipeline_a.manifest()
        )

        pipeline_manifest_b = (
            pipeline_b.manifest()
        )

        ok = (
            manifest_a
            == manifest_b
            and pipeline_manifest_a
            == pipeline_manifest_b
            and manifest_a.get(
                "owner"
            )
            == "blot."
            and manifest_a.get(
                "orchestrator"
            )
            == "opus"
            and manifest_a.get(
                "authority_effect"
            )
            == "none"
            and manifest_a.get(
                "projection_only"
            )
            is True
            and manifest_a.get(
                "typed_segues"
            )
            is True
            and manifest_a.get(
                "instance_first"
            )
            is True
            and manifest_a.get(
                "verification_lock"
            )
            is True
        )

        return VerificationCheck(
            check_id=(
                "reconstruction-entrypoints"
            ),
            ok=ok,
            category="integration",
            detail=(
                "passed"
                if ok
                else "reconstruction entrypoint invariant failed"
            ),
            digest=_digest(
                {
                    "integration":
                        manifest_a,

                    "pipeline":
                        pipeline_manifest_a,
                }
            ),
        )

    except Exception as exc:
        return VerificationCheck(
            check_id=(
                "reconstruction-entrypoints"
            ),
            ok=False,
            category="integration",
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def _check_stage_count(
) -> VerificationCheck:
    try:
        module = importlib.import_module(
            "runtime.translucent.blot_reconstruction"
        )

        stages = getattr(
            module,
            "all_stages",
        )

        rung_counts = {
            1: 0,
            2: 0,
            3: 0,
        }

        stage_ids: set[str] = set()

        duplicate = False

        for stage in stages:
            rung = int(
                stage.rung
            )

            if rung not in rung_counts:
                return VerificationCheck(
                    check_id="stage-contract",
                    ok=False,
                    category="architecture",
                    detail=(
                        f"invalid rung: {rung}"
                    ),
                )

            rung_counts[
                rung
            ] += 1

            if stage.stage_id in stage_ids:
                duplicate = True

            stage_ids.add(
                stage.stage_id
            )

        ok = (
            len(
                stages
            )
            == 92
            and rung_counts
            == {
                1: 32,
                2: 28,
                3: 32,
            }
            and not duplicate
        )

        return VerificationCheck(
            check_id="stage-contract",
            ok=ok,
            category="architecture",
            detail=(
                "passed"
                if ok
                else _canonical(
                    {
                        "total":
                            len(
                                stages
                            ),

                        "rungs":
                            rung_counts,

                        "duplicate":
                            duplicate,
                    }
                )
            ),
            digest=_digest(
                {
                    "stage_ids":
                        [
                            stage.stage_id
                            for stage in stages
                        ],

                    "rung_counts":
                        rung_counts,
                }
            ),
        )

    except Exception as exc:
        return VerificationCheck(
            check_id="stage-contract",
            ok=False,
            category="architecture",
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def _check_opus_boundary(
) -> VerificationCheck:
    try:
        module = importlib.import_module(
            "runtime.translucent.blot_opus"
        )

        provider = module.ProviderCapability(
            provider_id="verification-local",
            capabilities=(
                "*",
            ),
            deterministic=True,
            local=True,
            priority=1,
        )

        registry = module.ProviderRegistry(
            (
                provider,
            )
        )

        resolved = registry.resolve(
            "verification-capability",
            preferred=(
                "verification-local",
            ),
            deterministic_required=True,
        )

        ok = (
            len(
                resolved
            )
            == 1
            and resolved[
                0
            ].provider_id
            == "verification-local"
            and module.authority_effect
            == "none"
            and module.projection_only
            is True
        )

        return VerificationCheck(
            check_id="opus-boundary",
            ok=ok,
            category="orchestration",
            detail=(
                "passed"
                if ok
                else "opus provider boundary invariant failed"
            ),
            digest=_digest(
                [
                    item.normalized()
                    for item in resolved
                ]
            ),
        )

    except Exception as exc:
        return VerificationCheck(
            check_id="opus-boundary",
            ok=False,
            category="orchestration",
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def _check_svg_legacy_projection(
) -> VerificationCheck:
    try:
        runtime_module = importlib.import_module(
            "runtime.translucent.svg.runtime"
        )

        blot_module = importlib.import_module(
            "runtime.translucent.svg.blot"
        )

        runtime = (
            runtime_module
            .TranslucentSVGRuntime()
        )

        blot_module.register(
            runtime,
            replace=True,
        )

        payload: dict[str, Any] = {
            "authority_effect":
                "none",

            "projection_only":
                True,

            "authoritative":
                False,

            "width":
                256,

            "height":
                256,

            "shards":
                [
                    {
                        "kind":
                            "circle",

                        "shard_id":
                            "verification-circle",

                        "parameters":
                            {
                                "radius":
                                    32,
                            },
                    },
                ],

            "instances":
                [
                    {
                        "instance_id":
                            "verification-a",

                        "shard_id":
                            "verification-circle",

                        "transform":
                            {
                                "x":
                                    -40,

                                "y":
                                    0,

                                "scale_x":
                                    1,

                                "scale_y":
                                    1,
                            },

                        "paint":
                            {
                                "fill":
                                    "#d9b44a",

                                "stroke":
                                    "#11151a",

                                "stroke_width":
                                    2,
                            },
                    },
                    {
                        "instance_id":
                            "verification-b",

                        "shard_id":
                            "verification-circle",

                        "transform":
                            {
                                "x":
                                    40,

                                "y":
                                    0,

                                "scale_x":
                                    -1,

                                "scale_y":
                                    1,
                            },

                        "paint":
                            {
                                "fill":
                                    "#d9b44a",

                                "stroke":
                                    "#11151a",

                                "stroke_width":
                                    2,
                            },
                    },
                ],

            "segues":
                [
                    {
                        "kind":
                            "mirror",

                        "source":
                            "verification-a",

                        "target":
                            "verification-b",
                    },
                ],
        }

        payload[
            "digest"
        ] = _digest(
            payload
        )

        first = runtime.render(
            "blot",
            payload,
            renderer="blot",
        )

        second = runtime.render(
            "blot",
            payload,
            renderer="blot",
        )

        root = runtime.parse(
            first
        )

        ok = (
            first
            == second
            and root.tag
            == (
                "{"
                + runtime_module.SVG_NS
                + "}svg"
            )
            and blot_module.authority_effect
            == "none"
            and blot_module.manifest().get(
                "projection_only"
            )
            is True
            and blot_module.manifest().get(
                "authoritative"
            )
            is False
        )

        return VerificationCheck(
            check_id=(
                "svg-legacy-projection"
            ),
            ok=ok,
            category="compatibility",
            detail=(
                "passed"
                if ok
                else "legacy svg projection invariant failed"
            ),
            digest=_digest(
                first
            ),
        )

    except Exception as exc:
        return VerificationCheck(
            check_id=(
                "svg-legacy-projection"
            ),
            ok=False,
            category="compatibility",
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def _check_svg_reconstruction_projection(
) -> VerificationCheck:
    try:
        reconstruction_module = (
            importlib.import_module(
                "runtime.translucent.blot_reconstruction"
            )
        )

        svg_module = importlib.import_module(
            "runtime.translucent.svg.blot_reconstruction"
        )

        pipeline = (
            reconstruction_module
            .ReconstructionPipeline(
                source_digest=(
                    "verification-svg-source"
                )
            )
        )

        evidence_id = (
            pipeline.add_evidence(
                reconstruction_module.Evidence(
                    evidence_id=(
                        "verification-silhouette"
                    ),
                    kind="silhouette",
                    payload={
                        "region":
                            "primary",
                    },
                    confidence=1.0,
                    provenance=(
                        "verification",
                    ),
                )
            )
        )

        primitive_id = (
            pipeline.substantiate(
                reconstruction_module
                .ConstructionPrimitive(
                    primitive_id=(
                        "verification-ribbon"
                    ),
                    kind=(
                        "cubic-bezier-shape"
                    ),
                    parameters={
                        "d":
                            "M 10 50 "
                            "C 20 10 80 10 90 50 "
                            "C 80 90 20 90 10 50 Z",

                        "fill_rule":
                            "nonzero",
                    },
                    evidence_ids=(
                        evidence_id,
                    ),
                    confidence=1.0,
                    provenance=(
                        "verification",
                    ),
                )
            )
        )

        candidate_id = (
            pipeline.add_candidate(
                reconstruction_module.Candidate(
                    candidate_id=(
                        "verification-candidate"
                    ),
                    strategy=(
                        "semantic-bezier"
                    ),
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
        )

        contract = (
            pipeline
            .compile_execution_contract(
                candidate_id,
                (
                    reconstruction_module
                    .ExecutionStep(
                        step_id=(
                            "verification-build"
                        ),
                        stage_id=(
                            "bezier-build"
                        ),
                        operation=(
                            "construct-cubic-bezier"
                        ),
                        primitive_ids=(
                            primitive_id,
                        ),
                    ),
                ),
            )
        )

        graph = (
            pipeline
            .construction_graph()
        )

        primitive = graph[
            "primitives"
        ][0]

        gradient = (
            svg_module
            .SvgLinearGradient(
                gradient_id=(
                    "verification-material"
                ),
                x1=0,
                y1=0,
                x2=1,
                y2=1,
                stops=(
                    svg_module.SvgStop(
                        0.0,
                        "#101010",
                    ),
                    svg_module.SvgStop(
                        0.5,
                        "#f0f0f0",
                    ),
                    svg_module.SvgStop(
                        1.0,
                        "#202020",
                    ),
                ),
            )
        )

        path = (
            svg_module
            .path_from_primitive(
                primitive,
                fill=(
                    "url(#"
                    "verification-material"
                    ")"
                ),
            )
        )

        builder = (
            svg_module
            .ProjectionBuilder(
                contract,
                width=100,
                height=100,
            )
        )

        builder.add_gradient(
            gradient
        )

        builder.add(
            "geometry",
            path,
            primitive_ids=(
                primitive_id,
            ),
            step_id=(
                "verification-build"
            ),
        )

        document_a = (
            builder.document()
        )

        document_b = (
            builder.document()
        )

        svg_a = (
            document_a.render()
        )

        svg_b = (
            document_b.render()
        )

        receipt_a = (
            builder
            .projection_receipt()
        )

        receipt_b = (
            builder
            .projection_receipt()
        )

        ok = (
            svg_a
            == svg_b
            and receipt_a
            == receipt_b
            and receipt_a.get(
                "svg_digest"
            )
            == document_a.digest()
            and "verification-material"
            in svg_a
            and "primitive-verification-ribbon"
            in svg_a
            and "blot-geometry"
            in svg_a
            and svg_module.authority_effect
            == "none"
            and svg_module.projection_only
            is True
        )

        return VerificationCheck(
            check_id=(
                "svg-reconstruction-projection"
            ),
            ok=ok,
            category="projection",
            detail=(
                "passed"
                if ok
                else "reconstruction svg projection invariant failed"
            ),
            digest=_digest(
                {
                    "svg":
                        svg_a,

                    "receipt":
                        receipt_a,
                }
            ),
        )

    except Exception as exc:
        return VerificationCheck(
            check_id=(
                "svg-reconstruction-projection"
            ),
            ok=False,
            category="projection",
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def _check_pipeline_facade(
) -> VerificationCheck:
    try:
        module = importlib.import_module(
            "runtime.translucent.blot_pipeline"
        )

        request = (
            module
            .ReconstructionRequest(
                source_digest=(
                    "verification-pipeline-source"
                )
            )
        )

        pipeline_a = (
            module.BlotPipeline(
                request
            )
        )

        pipeline_b = (
            module.BlotPipeline(
                request
            )
        )

        manifest_a = (
            pipeline_a.manifest()
        )

        manifest_b = (
            pipeline_b.manifest()
        )

        profiles = (
            module
            .default_projection_profiles()
        )

        profile_ids = [
            profile.profile_id
            for profile in profiles
        ]

        ok = (
            manifest_a
            == manifest_b
            and profile_ids
            == [
                "presentation",
                "standard",
                "flat",
                "monochrome",
                "micro",
            ]
            and manifest_a.get(
                "authority_effect"
            )
            == "none"
            and manifest_a.get(
                "projection_only"
            )
            is True
            and manifest_a.get(
                "orchestration",
                {},
            ).get(
                "owner"
            )
            == "opus"
            and manifest_a.get(
                "construction",
                {},
            ).get(
                "owner"
            )
            == "blot."
            and manifest_a.get(
                "projection",
                {},
            ).get(
                "svg_is_derived"
            )
            is True
        )

        return VerificationCheck(
            check_id=(
                "pipeline-facade"
            ),
            ok=ok,
            category="integration",
            detail=(
                "passed"
                if ok
                else "pipeline facade invariant failed"
            ),
            digest=_digest(
                manifest_a
            ),
        )

    except Exception as exc:
        return VerificationCheck(
            check_id=(
                "pipeline-facade"
            ),
            ok=False,
            category="integration",
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def _check_integration_boundary(
) -> VerificationCheck:
    try:
        module = importlib.import_module(
            "runtime.translucent.blot_integration"
        )

        manifest_a = (
            module.integration_manifest()
        )

        manifest_b = (
            module.integration_manifest()
        )

        runtime = (
            module.reconstruction_runtime()
        )

        pipeline = runtime.pipeline(
            "verification-integration-source"
        )

        pipeline_manifest = (
            pipeline.manifest()
        )

        ok = (
            manifest_a
            == manifest_b
            and manifest_a.get(
                "owner"
            )
            == "blot."
            and manifest_a.get(
                "orchestrator"
            )
            == "opus"
            and manifest_a.get(
                "authority_effect"
            )
            == "none"
            and manifest_a.get(
                "projection_only"
            )
            is True
            and pipeline_manifest.get(
                "authority_effect"
            )
            == "none"
            and pipeline_manifest.get(
                "projection_only"
            )
            is True
        )

        return VerificationCheck(
            check_id=(
                "integration-boundary"
            ),
            ok=ok,
            category="integration",
            detail=(
                "passed"
                if ok
                else "integration boundary invariant failed"
            ),
            digest=_digest(
                {
                    "integration":
                        manifest_a,

                    "pipeline":
                        pipeline_manifest,
                }
            ),
        )

    except Exception as exc:
        return VerificationCheck(
            check_id=(
                "integration-boundary"
            ),
            ok=False,
            category="integration",
            detail=(
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def verify(
) -> VerificationReport:
    checks = (
        _run_selftest(
            "runtime.translucent.blot_reconstruction"
        ),
        _run_selftest(
            "runtime.translucent.blot_opus"
        ),
        _run_selftest(
            "runtime.translucent.svg.blot_reconstruction"
        ),
        _run_selftest(
            "runtime.translucent.blot_pipeline"
        ),
        _run_selftest(
            "runtime.translucent.blot_integration"
        ),
        _run_selftest(
            "runtime.translucent.blot"
        ),
        _run_selftest(
            "runtime.translucent.svg.blot",
            factory=(
                _svg_runtime_factory
            ),
        ),
        _check_core_compatibility(),
        _check_reconstruction_entrypoints(),
        _check_stage_count(),
        _check_opus_boundary(),
        _check_svg_legacy_projection(),
        _check_svg_reconstruction_projection(),
        _check_pipeline_facade(),
        _check_integration_boundary(),
    )

    return VerificationReport(
        checks=checks
    )


def assert_verified(
) -> dict[str, Any]:
    report = (
        verify()
        .normalized()
    )

    if not report[
        "ok"
    ]:
        failed = [
            check
            for check in report[
                "checks"
            ]
            if not check[
                "ok"
            ]
        ]

        raise BlotVerificationError(
            "blot. verification failed: "
            + _canonical(
                failed
            )
        )

    return report


def selftest(
) -> dict[str, Any]:
    report_a = (
        verify()
        .normalized()
    )

    report_b = (
        verify()
        .normalized()
    )

    deterministic = (
        report_a
        == report_b
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

        "deterministic_report":
            deterministic,

        "verification_passed":
            report_a[
                "ok"
            ]
            is True,
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

        "verification_digest":
            report_a[
                "digest"
            ],

        "verification":
            report_a,

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
    "BlotVerificationError",
    "VerificationCheck",
    "VerificationReport",
    "assert_verified",
    "authority_effect",
    "mutation_effect",
    "name",
    "projection_only",
    "schema",
    "selftest",
    "verify",
]


if __name__ == "__main__":
    print(
        json.dumps(
            verify().normalized(),
            indent=2,
            sort_keys=True,
        )
    )
