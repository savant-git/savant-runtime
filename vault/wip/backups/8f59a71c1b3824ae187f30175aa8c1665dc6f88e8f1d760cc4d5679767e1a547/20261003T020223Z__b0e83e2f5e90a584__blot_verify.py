#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from runtime.translucent import blot_integration
from runtime.translucent import blot_opus
from runtime.translucent import blot_pipeline
from runtime.translucent import blot_reconstruction
from runtime.translucent.svg import (
    blot_reconstruction as svg_blot_reconstruction,
)


name = "blot."
schema = "savant.translucent.blot.verify.v2"
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
        raise BlotVerificationError(
            f"{field_name} is required"
        )

    return result


@dataclass(frozen=True, slots=True)
class VerificationCheck:
    check_id: str
    category: str
    passed: bool
    observed: Any
    expected: Any
    causal_stage_id: str | None = None

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.check",

            "check_id":
                _text(
                    self.check_id,
                    "check_id",
                ),

            "category":
                _text(
                    self.category,
                    "category",
                ),

            "passed":
                bool(
                    self.passed
                ),

            "observed":
                self.observed,

            "expected":
                self.expected,

            "causal_stage_id":
                (
                    str(
                        self.causal_stage_id
                    ).strip()
                    if self.causal_stage_id
                    else None
                ),

            "authority_effect":
                "none",

            "mutation_effect":
                "none",
        }

        body["digest"] = _digest(body)

        return body


@dataclass(frozen=True, slots=True)
class VerificationReport:
    checks: tuple[
        VerificationCheck,
        ...
    ]

    def normalized(self) -> dict[str, Any]:
        normalized_checks = [
            check.normalized()
            for check in self.checks
        ]

        failures = [
            check
            for check in normalized_checks
            if not check[
                "passed"
            ]
        ]

        body = {
            "schema":
                f"{schema}.report",

            "name":
                name,

            "accepted":
                not failures,

            "check_count":
                len(
                    normalized_checks
                ),

            "passed_count":
                sum(
                    1
                    for check
                    in normalized_checks
                    if check[
                        "passed"
                    ]
                ),

            "failed_count":
                len(
                    failures
                ),

            "checks":
                normalized_checks,

            "failure_routes":
                [
                    {
                        "check_id":
                            failure[
                                "check_id"
                            ],

                        "category":
                            failure[
                                "category"
                            ],

                        "causal_stage_id":
                            failure[
                                "causal_stage_id"
                            ],
                    }
                    for failure
                    in failures
                ],

            "verification_lock": [
                "render",
                "measure",
                "compare",
                "accept-or-reject",
            ],

            "authority_effect":
                authority_effect,

            "mutation_effect":
                mutation_effect,

            "projection_only":
                projection_only,
        }

        body["digest"] = _digest(body)

        return body


class VerificationLock:
    def __init__(
        self,
        failure_router: Callable[
            [str],
            str
        ] | None = None,
    ) -> None:
        self.failure_router = (
            failure_router
        )

        self._checks: dict[
            str,
            VerificationCheck,
        ] = {}

    def _route(
        self,
        category: str,
    ) -> str | None:
        if self.failure_router is None:
            return None

        return self.failure_router(
            category
        )

    def add(
        self,
        check_id: str,
        category: str,
        *,
        observed: Any,
        expected: Any,
        passed: bool | None = None,
        causal_stage_id: str | None = None,
    ) -> str:
        check_id = _text(
            check_id,
            "check_id",
        )

        category = _text(
            category,
            "category",
        )

        if passed is None:
            passed = (
                observed
                == expected
            )

        if (
            not passed
            and causal_stage_id
            is None
        ):
            causal_stage_id = (
                self._route(
                    category
                )
            )

        check = VerificationCheck(
            check_id=check_id,
            category=category,
            passed=bool(
                passed
            ),
            observed=observed,
            expected=expected,
            causal_stage_id=(
                causal_stage_id
            ),
        )

        normalized = (
            check.normalized()
        )

        existing = self._checks.get(
            check_id
        )

        if existing is not None:
            if (
                existing.normalized()
                != normalized
            ):
                raise BlotVerificationError(
                    "verification check identity "
                    f"conflict: {check_id}"
                )

            return check_id

        self._checks[
            check_id
        ] = check

        return check_id

    def report(
        self,
    ) -> VerificationReport:
        return VerificationReport(
            checks=tuple(
                self._checks[
                    check_id
                ]
                for check_id
                in sorted(
                    self._checks
                )
            )
        )


def _module_contract_checks(
) -> tuple[
    VerificationCheck,
    ...
]:
    modules = {
        "reconstruction":
            blot_reconstruction,

        "opus":
            blot_opus,

        "pipeline":
            blot_pipeline,

        "integration":
            blot_integration,

        "svg-reconstruction":
            svg_blot_reconstruction,
    }

    checks: list[
        VerificationCheck
    ] = []

    for module_name, module in modules.items():
        checks.extend(
            (
                VerificationCheck(
                    check_id=(
                        f"{module_name}-name"
                    ),
                    category="identity",
                    passed=(
                        getattr(
                            module,
                            "name",
                            None,
                        )
                        == "blot."
                    ),
                    observed=getattr(
                        module,
                        "name",
                        None,
                    ),
                    expected="blot.",
                ),
                VerificationCheck(
                    check_id=(
                        f"{module_name}-authority"
                    ),
                    category="authority",
                    passed=(
                        getattr(
                            module,
                            "authority_effect",
                            None,
                        )
                        == "none"
                    ),
                    observed=getattr(
                        module,
                        "authority_effect",
                        None,
                    ),
                    expected="none",
                ),
                VerificationCheck(
                    check_id=(
                        f"{module_name}-projection"
                    ),
                    category="projection",
                    passed=(
                        getattr(
                            module,
                            "projection_only",
                            None,
                        )
                        is True
                    ),
                    observed=getattr(
                        module,
                        "projection_only",
                        None,
                    ),
                    expected=True,
                ),
            )
        )

    return tuple(
        checks
    )


def _architecture_checks(
) -> tuple[
    VerificationCheck,
    ...
]:
    opus_manifest = (
        blot_opus.manifest()
    )

    integration_manifest = (
        blot_integration.manifest()
    )

    return (
        VerificationCheck(
            check_id=(
                "opus-execution-owner"
            ),
            category="ownership",
            passed=(
                opus_manifest[
                    "execution_owner"
                ]
                == "opus"
            ),
            observed=(
                opus_manifest[
                    "execution_owner"
                ]
            ),
            expected="opus",
        ),
        VerificationCheck(
            check_id=(
                "opus-routing-owner"
            ),
            category="ownership",
            passed=(
                opus_manifest[
                    "routing_owner"
                ]
                == "opus"
            ),
            observed=(
                opus_manifest[
                    "routing_owner"
                ]
            ),
            expected="opus",
        ),
        VerificationCheck(
            check_id=(
                "blot-no-provider-registry"
            ),
            category="ownership",
            passed=(
                opus_manifest[
                    "provider_registry_owned"
                ]
                is False
            ),
            observed=(
                opus_manifest[
                    "provider_registry_owned"
                ]
            ),
            expected=False,
        ),
        VerificationCheck(
            check_id=(
                "blot-no-provider-execution"
            ),
            category="ownership",
            passed=(
                opus_manifest[
                    "provider_execution_owned"
                ]
                is False
            ),
            observed=(
                opus_manifest[
                    "provider_execution_owned"
                ]
            ),
            expected=False,
        ),
        VerificationCheck(
            check_id=(
                "blot-no-retry-policy"
            ),
            category="ownership",
            passed=(
                opus_manifest[
                    "provider_retry_owned"
                ]
                is False
            ),
            observed=(
                opus_manifest[
                    "provider_retry_owned"
                ]
            ),
            expected=False,
        ),
        VerificationCheck(
            check_id=(
                "blot-no-fallback-policy"
            ),
            category="ownership",
            passed=(
                opus_manifest[
                    "provider_fallback_owned"
                ]
                is False
            ),
            observed=(
                opus_manifest[
                    "provider_fallback_owned"
                ]
            ),
            expected=False,
        ),
        VerificationCheck(
            check_id=(
                "projection-not-authority"
            ),
            category="projection",
            passed=(
                integration_manifest[
                    "projection_is_authority"
                ]
                is False
            ),
            observed=(
                integration_manifest[
                    "projection_is_authority"
                ]
            ),
            expected=False,
        ),
        VerificationCheck(
            check_id=(
                "svg-derived"
            ),
            category="projection",
            passed=(
                integration_manifest[
                    "svg_is_derived"
                ]
                is True
            ),
            observed=(
                integration_manifest[
                    "svg_is_derived"
                ]
            ),
            expected=True,
        ),
    )


def verify_projection(
    *,
    svg: str,
    document: Mapping[
        str,
        Any
    ],
    execution_contract: Mapping[
        str,
        Any
    ],
    projection_receipt: Mapping[
        str,
        Any
    ],
    expected: Mapping[
        str,
        Any
    ] | None = None,
    failure_router: Callable[
        [str],
        str
    ] | None = None,
) -> VerificationReport:
    lock = VerificationLock(
        failure_router
    )

    svg_digest = _digest(
        svg
    )

    lock.add(
        "svg-digest",
        "deterministic-replay",
        observed=svg_digest,
        expected=projection_receipt.get(
            "svg_digest"
        ),
    )

    lock.add(
        "document-digest",
        "deterministic-replay",
        observed=document.get(
            "digest"
        ),
        expected=projection_receipt.get(
            "svg_document_digest"
        ),
    )

    lock.add(
        "execution-contract-digest",
        "deterministic-replay",
        observed=execution_contract.get(
            "digest"
        ),
        expected=projection_receipt.get(
            "execution_contract_digest"
        ),
    )

    lock.add(
        "construction-digest",
        "deterministic-replay",
        observed=execution_contract.get(
            "construction_digest"
        ),
        expected=projection_receipt.get(
            "construction_digest"
        ),
    )

    lock.add(
        "execution-ready",
        "execution-readiness",
        observed=execution_contract.get(
            "execution_ready"
        ),
        expected=True,
    )

    lock.add(
        "projection-authority",
        "projection",
        observed=projection_receipt.get(
            "projection_is_authority"
        ),
        expected=False,
    )

    lock.add(
        "svg-derived",
        "projection",
        observed=projection_receipt.get(
            "svg_is_derived"
        ),
        expected=True,
    )

    lock.add(
        "no-embedded-raster",
        "structural-quality",
        observed=(
            "<image"
            not in svg.lower()
        ),
        expected=True,
    )

    lock.add(
        "svg-root",
        "renderer-stability",
        observed=(
            "<svg"
            in svg.lower()
        ),
        expected=True,
    )

    expected_values = dict(
        expected or {}
    )

    category_aliases = {
        "topology":
            "topology",

        "silhouette":
            "silhouette",

        "landmarks":
            "landmarks",

        "negative_space":
            "negative-space",

        "curvature":
            "curvature",

        "proportions":
            "proportions",

        "color":
            "color",

        "gradients":
            "gradients",

        "material_appearance":
            "material",

        "lighting":
            "lighting",

        "masks":
            "masks",

        "clipping":
            "clipping",

        "optical_size_behavior":
            "optical-size",

        "editability":
            "editability",

        "primitive_count":
            "primitive-count",

        "anchor_economy":
            "anchor-economy",

        "renderer_stability":
            "renderer-stability",

        "deterministic_replay":
            "deterministic-replay",

        "lineage":
            "lineage",

        "provenance":
            "provenance",
    }

    observed_metrics = (
        document.get(
            "metadata",
            {}
        )
    )

    for key, category in (
        category_aliases.items()
    ):
        if key not in expected_values:
            continue

        lock.add(
            f"quality-{key}",
            category,
            observed=(
                observed_metrics.get(
                    key
                )
            ),
            expected=(
                expected_values[
                    key
                ]
            ),
        )

    return lock.report()


def selftest() -> dict[str, Any]:
    checks = (
        _module_contract_checks()
        + _architecture_checks()
    )

    report_a = VerificationReport(
        checks=checks
    ).normalized()

    report_b = VerificationReport(
        checks=checks
    ).normalized()

    self_checks = {
        "accepted":
            report_a[
                "accepted"
            ]
            is True,

        "deterministic":
            report_a
            == report_b,

        "checks_present":
            report_a[
                "check_count"
            ]
            > 0,

        "no_failures":
            report_a[
                "failed_count"
            ]
            == 0,

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
    }

    result = {
        "schema":
            f"{schema}.selftest",

        "ok":
            all(
                self_checks.values()
            ),

        "checks":
            self_checks,

        "verification_report":
            report_a,

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,

        "projection_only":
            projection_only,
    }

    result["digest"] = _digest(
        result
    )

    return result


def manifest() -> dict[str, Any]:
    body = {
        "schema":
            schema,

        "name":
            name,

        "verification_lock": [
            "render",
            "measure",
            "compare",
            "accept-or-reject",
        ],

        "checks": [
            "topology",
            "silhouette",
            "landmarks",
            "negative-space",
            "curvature",
            "proportions",
            "color",
            "gradients",
            "material",
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
        ],

        "failure_routing":
            "earliest-causal-stage",

        "provider_registry_owned":
            False,

        "provider_execution_owned":
            False,

        "provider_routing_owned":
            False,

        "provider_retry_policy_owned":
            False,

        "provider_fallback_policy_owned":
            False,

        "projection_is_authority":
            False,

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,

        "projection_only":
            projection_only,
    }

    body["digest"] = _digest(
        body
    )

    return body


__all__ = [
    "BlotVerificationError",
    "VerificationCheck",
    "VerificationLock",
    "VerificationReport",
    "authority_effect",
    "manifest",
    "mutation_effect",
    "name",
    "projection_only",
    "schema",
    "selftest",
    "verify_projection",
]


if __name__ == "__main__":
    print(
        json.dumps(
            selftest(),
            indent=2,
            sort_keys=True,
        )
    )
