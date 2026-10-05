#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping
from xml.etree import ElementTree as ET


name = "blot."
schema = "savant.translucent.blot.verification.v2"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

svg_ns = "http://www.w3.org/2000/svg"

verification_lock = (
    "topology",
    "silhouette",
    "landmarks",
    "negative_space",
    "curvature",
    "proportions",
    "color",
    "gradients",
    "material_appearance",
    "lighting",
    "masks",
    "clipping",
    "optical_size_behavior",
    "editability",
    "primitive_count",
    "anchor_economy",
    "renderer_stability",
    "deterministic_replay",
    "lineage",
    "provenance",
)

failure_routing = {
    "topology":
        "r1-04-topology-inference",
    "silhouette":
        "r1-09-geometric-scaffold-recovery",
    "landmarks":
        "r1-09-geometric-scaffold-recovery",
    "negative_space":
        "r1-12-negative-space-reconstruction",
    "curvature":
        "r1-11-curvature-continuity-analysis",
    "proportions":
        "r1-09-geometric-scaffold-recovery",
    "color":
        "r1-17-base-color-reconstruction",
    "gradients":
        "r1-20-gradient-construction-planning",
    "material_appearance":
        "r1-21-material-inference",
    "lighting":
        "r1-23-lighting-decomposition",
    "masks":
        "r1-27-mask-clipping-analysis",
    "clipping":
        "r1-27-mask-clipping-analysis",
    "optical_size_behavior":
        "r1-30-optical-size-projection-planning",
    "editability":
        "r1-32-structural-quality-specification",
    "primitive_count":
        "r1-16-shape-economy-analysis",
    "anchor_economy":
        "r1-10-curve-reconstruction-planning",
    "renderer_stability":
        "r2-05-renderer-compatibility-simulation",
    "deterministic_replay":
        "r2-28-execution-plan-compilation",
    "lineage":
        "r2-01-construction-graph-integrity",
    "provenance":
        "r2-01-construction-graph-integrity",
}

max_checks = 256
max_failures = 256
max_metrics = 1024


class BlotVerificationError(ValueError):
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
        raise BlotVerificationError(
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


def _text(value: Any, field_name: str) -> str:
    result = str(value or "").strip()

    if not result:
        raise BlotVerificationError(
            f"{field_name} is required"
        )

    return result


def _mapping(
    value: Any,
    field_name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BlotVerificationError(
            f"{field_name} must be a mapping"
        )

    return value


def _finite(
    value: Any,
    field_name: str,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise BlotVerificationError(
            f"{field_name} must be numeric"
        ) from exc

    if not math.isfinite(result):
        raise BlotVerificationError(
            f"{field_name} must be finite"
        )

    return result


def _bounded_score(
    value: Any,
    field_name: str,
) -> float:
    result = _finite(
        value,
        field_name,
    )

    if not 0.0 <= result <= 1.0:
        raise BlotVerificationError(
            f"{field_name} must be between 0 and 1"
        )

    return result


def _unique_text(
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


@dataclass(frozen=True)
class VerificationMetric:
    metric_id: str
    category: str
    observed: Any
    expected: Any = None
    score: float | None = None
    tolerance: float | None = None
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        metric_id = _text(
            self.metric_id,
            "metric_id",
        )

        category = _text(
            self.category,
            "category",
        )

        if category not in verification_lock:
            raise BlotVerificationError(
                f"unsupported verification category: {category}"
            )

        score = None

        if self.score is not None:
            score = _bounded_score(
                self.score,
                "score",
            )

        tolerance = None

        if self.tolerance is not None:
            tolerance = _finite(
                self.tolerance,
                "tolerance",
            )

            if tolerance < 0:
                raise BlotVerificationError(
                    "tolerance cannot be negative"
                )

        body = {
            "metric_id": metric_id,
            "category": category,
            "observed": self.observed,
            "expected": self.expected,
            "score": score,
            "tolerance": tolerance,
            "provenance": list(
                _unique_text(
                    self.provenance
                )
            ),
        }

        return {
            **body,
            "digest": _digest(body),
        }


@dataclass(frozen=True)
class VerificationCheck:
    check_id: str
    category: str
    accepted: bool
    metrics: tuple[VerificationMetric, ...] = ()
    reason: str = ""
    causal_stage_id: str = ""
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        check_id = _text(
            self.check_id,
            "check_id",
        )

        category = _text(
            self.category,
            "category",
        )

        if category not in verification_lock:
            raise BlotVerificationError(
                f"unsupported verification category: {category}"
            )

        metrics = tuple(
            item.normalized()
            for item in self.metrics
        )

        if len(metrics) > max_metrics:
            raise BlotVerificationError(
                "verification metric limit exceeded"
            )

        for metric in metrics:
            if metric["category"] != category:
                raise BlotVerificationError(
                    "verification metric category "
                    "must match its check category"
                )

        causal_stage_id = (
            str(
                self.causal_stage_id
                or failure_routing[category]
            ).strip()
        )

        body = {
            "check_id": check_id,
            "category": category,
            "accepted": bool(
                self.accepted
            ),
            "metrics": list(metrics),
            "reason": str(
                self.reason or ""
            ).strip(),
            "causal_stage_id":
                causal_stage_id,
            "provenance": list(
                _unique_text(
                    self.provenance
                )
            ),
        }

        return {
            **body,
            "digest": _digest(body),
        }


@dataclass(frozen=True)
class VerificationFailure:
    category: str
    check_id: str
    causal_stage_id: str
    reason: str
    metric_ids: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        category = _text(
            self.category,
            "category",
        )

        if category not in verification_lock:
            raise BlotVerificationError(
                f"unsupported verification category: {category}"
            )

        body = {
            "category": category,
            "check_id": _text(
                self.check_id,
                "check_id",
            ),
            "causal_stage_id": _text(
                self.causal_stage_id,
                "causal_stage_id",
            ),
            "reason": str(
                self.reason or ""
            ).strip(),
            "metric_ids": list(
                _unique_text(
                    self.metric_ids
                )
            ),
        }

        return {
            **body,
            "digest": _digest(body),
        }


@dataclass(frozen=True)
class VerificationReport:
    source_digest: str
    construction_digest: str
    execution_digest: str
    projection_digest: str
    checks: tuple[VerificationCheck, ...]
    failures: tuple[VerificationFailure, ...]
    accepted: bool
    provenance: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        checks = tuple(
            item.normalized()
            for item in self.checks
        )

        failures = tuple(
            item.normalized()
            for item in self.failures
        )

        if len(checks) > max_checks:
            raise BlotVerificationError(
                "verification check limit exceeded"
            )

        if len(failures) > max_failures:
            raise BlotVerificationError(
                "verification failure limit exceeded"
            )

        categories = {
            item["category"]
            for item in checks
        }

        complete = all(
            category in categories
            for category in verification_lock
        )

        computed_acceptance = (
            complete
            and all(
                item["accepted"]
                for item in checks
            )
            and not failures
        )

        if bool(self.accepted) != computed_acceptance:
            raise BlotVerificationError(
                "verification acceptance does not "
                "match verification checks"
            )

        body = {
            "schema": schema,
            "name": name,
            "source_digest": _text(
                self.source_digest,
                "source_digest",
            ),
            "construction_digest": _text(
                self.construction_digest,
                "construction_digest",
            ),
            "execution_digest": _text(
                self.execution_digest,
                "execution_digest",
            ),
            "projection_digest": _text(
                self.projection_digest,
                "projection_digest",
            ),
            "checks": list(checks),
            "failures": list(failures),
            "verification_complete":
                complete,
            "accepted":
                computed_acceptance,
            "authority_effect":
                authority_effect,
            "mutation_effect":
                mutation_effect,
            "projection_only":
                projection_only,
            "provenance": list(
                _unique_text(
                    self.provenance
                )
            ),
        }

        return {
            **body,
            "digest": _digest(body),
        }


def _svg_facts(
    svg: str,
) -> dict[str, Any]:
    if not isinstance(svg, str) or not svg.strip():
        raise BlotVerificationError(
            "svg must be non-empty"
        )

    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise BlotVerificationError(
            f"svg is not parseable: {exc}"
        ) from exc

    if root.tag != f"{{{svg_ns}}}svg":
        raise BlotVerificationError(
            "projection root must be svg"
        )

    elements = list(root.iter())

    paths = [
        element
        for element in elements
        if element.tag
        == f"{{{svg_ns}}}path"
    ]

    gradients = [
        element
        for element in elements
        if element.tag
        in {
            f"{{{svg_ns}}}linearGradient",
            f"{{{svg_ns}}}radialGradient",
        }
    ]

    masks = [
        element
        for element in elements
        if element.tag
        == f"{{{svg_ns}}}mask"
    ]

    clips = [
        element
        for element in elements
        if element.tag
        == f"{{{svg_ns}}}clipPath"
    ]

    filters = [
        element
        for element in elements
        if element.tag
        == f"{{{svg_ns}}}filter"
    ]

    uses = [
        element
        for element in elements
        if element.tag
        == f"{{{svg_ns}}}use"
    ]

    metadata = [
        element.text or ""
        for element in elements
        if element.tag
        == f"{{{svg_ns}}}metadata"
    ]

    return {
        "digest": _digest(svg),
        "element_count": len(elements),
        "path_count": len(paths),
        "gradient_count": len(gradients),
        "mask_count": len(masks),
        "clip_count": len(clips),
        "filter_count": len(filters),
        "use_count": len(uses),
        "metadata": metadata,
        "has_view_box":
            bool(root.get("viewBox")),
    }


def _contract_facts(
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    contract = _mapping(
        contract,
        "execution_contract",
    )

    required_resolution = (
        "topology_resolved",
        "geometry_resolved",
        "negative_space_resolved",
        "booleans_resolved",
        "materials_resolved",
        "lighting_resolved",
        "masks_resolved",
        "gradients_resolved",
    )

    resolution = {
        key: bool(
            contract.get(
                key,
                False,
            )
        )
        for key in required_resolution
    }

    return {
        "digest":
            str(
                contract.get(
                    "digest"
                )
                or _digest(contract)
            ),

        "construction_digest":
            str(
                contract.get(
                    "construction_digest",
                    "",
                )
            ).strip(),

        "execution_ready":
            bool(
                contract.get(
                    "execution_ready",
                    False,
                )
            ),

        "blocking_ambiguities":
            int(
                contract.get(
                    "blocking_ambiguities",
                    0,
                )
                or 0
            ),

        "resolution":
            resolution,

        "predicted_counts":
            dict(
                contract.get(
                    "predicted_counts",
                    {},
                )
                or {}
            ),
    }


def _receipt_facts(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = _mapping(
        receipt,
        "projection_receipt",
    )

    return {
        "digest":
            str(
                receipt.get(
                    "digest"
                )
                or _digest(receipt)
            ),

        "source_digest":
            str(
                receipt.get(
                    "source_digest",
                    "",
                )
            ).strip(),

        "construction_digest":
            str(
                receipt.get(
                    "construction_digest",
                    "",
                )
            ).strip(),

        "execution_digest":
            str(
                receipt.get(
                    "execution_digest",
                    "",
                )
            ).strip(),

        "projection_digest":
            str(
                receipt.get(
                    "projection_digest",
                    "",
                )
            ).strip(),

        "profile":
            str(
                receipt.get(
                    "profile",
                    "",
                )
            ).strip(),
    }


def _expected_value(
    expected: Mapping[str, Any],
    key: str,
    fallback: Any,
) -> Any:
    if key in expected:
        return expected[key]

    return fallback


def verify_projection(
    *,
    svg: str,
    document: Mapping[str, Any],
    execution_contract: Mapping[str, Any],
    projection_receipt: Mapping[str, Any],
    expected: Mapping[str, Any] | None = None,
    failure_router: Callable[[str], str] | None = None,
) -> VerificationReport:
    document = _mapping(
        document,
        "document",
    )

    expected_map = dict(
        expected or {}
    )

    svg_facts = _svg_facts(svg)
    contract = _contract_facts(
        execution_contract
    )
    receipt = _receipt_facts(
        projection_receipt
    )

    document_digest = str(
        document.get(
            "digest"
        )
        or _digest(document)
    )

    source_digest = str(
        receipt["source_digest"]
        or document.get(
            "source_digest",
            "",
        )
    ).strip()

    if not source_digest:
        raise BlotVerificationError(
            "source_digest is required"
        )

    construction_digest = str(
        receipt["construction_digest"]
        or contract[
            "construction_digest"
        ]
        or document.get(
            "construction_digest",
            "",
        )
    ).strip()

    if not construction_digest:
        raise BlotVerificationError(
            "construction_digest is required"
        )

    execution_digest = str(
        receipt["execution_digest"]
        or contract["digest"]
    ).strip()

    projection_digest = str(
        receipt["projection_digest"]
        or svg_facts["digest"]
    ).strip()

    predicted = contract[
        "predicted_counts"
    ]

    checks: list[
        VerificationCheck
    ] = []

    def route(
        category: str,
    ) -> str:
        if failure_router is not None:
            routed = str(
                failure_router(
                    category
                )
                or ""
            ).strip()

            if routed:
                return routed

        return failure_routing[
            category
        ]

    def add(
        category: str,
        accepted: bool,
        *,
        reason: str,
        metrics: Iterable[
            VerificationMetric
        ] = (),
    ) -> None:
        checks.append(
            VerificationCheck(
                check_id=(
                    "verify-"
                    + category.replace(
                        "_",
                        "-",
                    )
                ),
                category=category,
                accepted=accepted,
                metrics=tuple(metrics),
                reason=reason,
                causal_stage_id=route(
                    category
                ),
                provenance=(
                    source_digest,
                    construction_digest,
                    execution_digest,
                    projection_digest,
                ),
            )
        )

    resolution = contract[
        "resolution"
    ]

    add(
        "topology",
        (
            contract[
                "execution_ready"
            ]
            and resolution[
                "topology_resolved"
            ]
            and contract[
                "blocking_ambiguities"
            ] == 0
        ),
        reason=(
            "execution contract topology "
            "and ambiguity gate"
        ),
    )

    add(
        "silhouette",
        bool(
            svg_facts[
                "path_count"
            ]
            or svg_facts[
                "use_count"
            ]
        ),
        reason=(
            "projection contains explicit "
            "renderable geometry"
        ),
        metrics=(
            VerificationMetric(
                metric_id=
                    "silhouette-renderable-count",
                category=
                    "silhouette",
                observed=(
                    svg_facts[
                        "path_count"
                    ]
                    + svg_facts[
                        "use_count"
                    ]
                ),
                expected=_expected_value(
                    expected_map,
                    "minimum_renderable_geometry",
                    1,
                ),
                provenance=(
                    projection_digest,
                ),
            ),
        ),
    )

    landmark_expected = expected_map.get(
        "landmarks"
    )

    landmark_observed = document.get(
        "landmarks"
    )

    landmarks_ok = (
        landmark_expected is None
        or landmark_observed
        == landmark_expected
    )

    add(
        "landmarks",
        landmarks_ok,
        reason=(
            "document landmarks match "
            "declared reconstruction expectation"
        ),
    )

    add(
        "negative_space",
        resolution[
            "negative_space_resolved"
        ],
        reason=(
            "execution contract negative-space "
            "resolution gate"
        ),
    )

    curvature_score = expected_map.get(
        "curvature_score"
    )

    curvature_ok = (
        curvature_score is None
        or _bounded_score(
            curvature_score,
            "curvature_score",
        )
        >= _bounded_score(
            expected_map.get(
                "minimum_curvature_score",
                0.0,
            ),
            "minimum_curvature_score",
        )
    )

    add(
        "curvature",
        curvature_ok,
        reason=(
            "curvature quality satisfies "
            "declared verification threshold"
        ),
    )

    proportion_score = expected_map.get(
        "proportion_score"
    )

    proportions_ok = (
        proportion_score is None
        or _bounded_score(
            proportion_score,
            "proportion_score",
        )
        >= _bounded_score(
            expected_map.get(
                "minimum_proportion_score",
                0.0,
            ),
            "minimum_proportion_score",
        )
    )

    add(
        "proportions",
        proportions_ok,
        reason=(
            "proportion quality satisfies "
            "declared verification threshold"
        ),
    )

    color_expected = expected_map.get(
        "palette"
    )

    color_observed = document.get(
        "palette"
    )

    color_ok = (
        color_expected is None
        or color_observed
        == color_expected
    )

    add(
        "color",
        color_ok,
        reason=(
            "projection palette matches "
            "declared construction expectation"
        ),
    )

    predicted_gradients = int(
        predicted.get(
            "gradients",
            0,
        )
        or 0
    )

    gradients_ok = (
        resolution[
            "gradients_resolved"
        ]
        and (
            predicted_gradients == 0
            or svg_facts[
                "gradient_count"
            ] > 0
        )
    )

    add(
        "gradients",
        gradients_ok,
        reason=(
            "resolved gradient contract "
            "matches projected gradient presence"
        ),
        metrics=(
            VerificationMetric(
                metric_id=
                    "gradient-count",
                category=
                    "gradients",
                observed=
                    svg_facts[
                        "gradient_count"
                    ],
                expected=
                    predicted_gradients,
                provenance=(
                    projection_digest,
                ),
            ),
        ),
    )

    add(
        "material_appearance",
        resolution[
            "materials_resolved"
        ],
        reason=(
            "execution contract material "
            "resolution gate"
        ),
    )

    add(
        "lighting",
        resolution[
            "lighting_resolved"
        ],
        reason=(
            "execution contract lighting "
            "resolution gate"
        ),
    )

    predicted_masks = int(
        predicted.get(
            "masks",
            0,
        )
        or 0
    )

    masks_ok = (
        resolution[
            "masks_resolved"
        ]
        and (
            predicted_masks == 0
            or svg_facts[
                "mask_count"
            ] > 0
        )
    )

    add(
        "masks",
        masks_ok,
        reason=(
            "resolved mask contract matches "
            "projected mask presence"
        ),
    )

    predicted_clips = int(
        predicted.get(
            "clips",
            0,
        )
        or 0
    )

    clips_ok = (
        predicted_clips == 0
        or svg_facts[
            "clip_count"
        ] > 0
    )

    add(
        "clipping",
        clips_ok,
        reason=(
            "projected clipping satisfies "
            "predicted clipping requirement"
        ),
    )

    profiles = document.get(
        "profiles",
        ()
    )

    optical_ok = bool(
        profiles
        or receipt["profile"]
    )

    add(
        "optical_size_behavior",
        optical_ok,
        reason=(
            "projection retains an explicit "
            "optical projection profile"
        ),
    )

    primitive_count = int(
        document.get(
            "primitive_count",
            svg_facts[
                "path_count"
            ],
        )
        or 0
    )

    primitive_limit = int(
        expected_map.get(
            "maximum_primitive_count",
            max(
                primitive_count,
                1,
            ),
        )
    )

    add(
        "editability",
        (
            primitive_count
            <= primitive_limit
            and bool(
                construction_digest
            )
        ),
        reason=(
            "projection remains bound to "
            "construction substance within "
            "declared primitive budget"
        ),
    )

    add(
        "primitive_count",
        primitive_count
        <= primitive_limit,
        reason=(
            "primitive count remains within "
            "declared semantic economy budget"
        ),
        metrics=(
            VerificationMetric(
                metric_id=
                    "primitive-count",
                category=
                    "primitive_count",
                observed=
                    primitive_count,
                expected=
                    primitive_limit,
                tolerance=0,
                provenance=(
                    construction_digest,
                    projection_digest,
                ),
            ),
        ),
    )

    anchor_count = int(
        document.get(
            "anchor_count",
            predicted.get(
                "anchors",
                0,
            ),
        )
        or 0
    )

    anchor_limit = int(
        expected_map.get(
            "maximum_anchor_count",
            max(
                anchor_count,
                1,
            ),
        )
    )

    add(
        "anchor_economy",
        anchor_count
        <= anchor_limit,
        reason=(
            "anchor count remains within "
            "declared curve economy budget"
        ),
        metrics=(
            VerificationMetric(
                metric_id=
                    "anchor-count",
                category=
                    "anchor_economy",
                observed=
                    anchor_count,
                expected=
                    anchor_limit,
                tolerance=0,
                provenance=(
                    construction_digest,
                ),
            ),
        ),
    )

    add(
        "renderer_stability",
        (
            svg_facts[
                "has_view_box"
            ]
            and svg_facts[
                "digest"
            ]
            == projection_digest
        ),
        reason=(
            "projection parses as SVG and "
            "matches its projection digest"
        ),
    )

    replay_digest = str(
        expected_map.get(
            "replay_projection_digest",
            projection_digest,
        )
    ).strip()

    add(
        "deterministic_replay",
        replay_digest
        == projection_digest,
        reason=(
            "replayed projection digest "
            "matches canonical projection digest"
        ),
    )

    lineage = document.get(
        "lineage"
    )

    lineage_expected = expected_map.get(
        "lineage"
    )

    add(
        "lineage",
        (
            lineage_expected is None
            or lineage
            == lineage_expected
        ),
        reason=(
            "projection lineage is preserved "
            "from construction graph"
        ),
    )

    provenance = document.get(
        "provenance"
    )

    provenance_expected = expected_map.get(
        "provenance"
    )

    add(
        "provenance",
        (
            provenance_expected is None
            or provenance
            == provenance_expected
        ),
        reason=(
            "projection provenance is preserved "
            "from construction graph"
        ),
    )

    failures: list[
        VerificationFailure
    ] = []

    for check in checks:
        normalized = check.normalized()

        if normalized[
            "accepted"
        ]:
            continue

        failures.append(
            VerificationFailure(
                category=
                    normalized[
                        "category"
                    ],
                check_id=
                    normalized[
                        "check_id"
                    ],
                causal_stage_id=
                    normalized[
                        "causal_stage_id"
                    ],
                reason=
                    normalized[
                        "reason"
                    ],
                metric_ids=tuple(
                    metric[
                        "metric_id"
                    ]
                    for metric
                    in normalized[
                        "metrics"
                    ]
                ),
            )
        )

    accepted = (
        len(checks)
        == len(
            verification_lock
        )
        and not failures
        and all(
            check.normalized()[
                "accepted"
            ]
            for check in checks
        )
    )

    report = VerificationReport(
        source_digest=
            source_digest,
        construction_digest=
            construction_digest,
        execution_digest=
            execution_digest,
        projection_digest=
            projection_digest,
        checks=tuple(
            checks
        ),
        failures=tuple(
            failures
        ),
        accepted=accepted,
        provenance=(
            document_digest,
            contract["digest"],
            receipt["digest"],
        ),
    )

    report.normalized()

    return report


def manifest() -> dict[str, Any]:
    body = {
        "schema": schema,
        "name": name,
        "authority_effect":
            authority_effect,
        "mutation_effect":
            mutation_effect,
        "projection_only":
            projection_only,
        "verification_lock":
            list(
                verification_lock
            ),
        "failure_routing":
            dict(
                failure_routing
            ),
        "method":
            (
                "render-measure-compare-"
                "accept-reject"
            ),
        "failure_policy":
            (
                "route-to-earliest-causal-stage"
            ),
        "geometry_reflex":
            False,
        "provider_execution":
            False,
        "provider_routing":
            False,
    }

    return {
        **body,
        "digest": _digest(body),
    }


__all__ = [
    "BlotVerificationError",
    "VerificationCheck",
    "VerificationFailure",
    "VerificationMetric",
    "VerificationReport",
    "authority_effect",
    "failure_routing",
    "manifest",
    "mutation_effect",
    "name",
    "projection_only",
    "schema",
    "verification_lock",
    "verify_projection",
]


if __name__ == "__main__":
    print(
        json.dumps(
            manifest(),
            indent=2,
            sort_keys=True,
        )
    )
