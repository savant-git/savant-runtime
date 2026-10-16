#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from runtime.opus_ai_adapter import OpusAIAdapter
from runtime.translucent.blot_pipeline import (
    BlotPipeline,
    ProjectionProfile,
    ReconstructionRequest,
    default_projection_profiles,
)
from runtime.translucent.blot_opus import (
    SelectionPolicy,
)


name = "blot."
schema = "savant.translucent.blot.integration.v2"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

owner = "blot."
orchestrator = "opus"

rungs = {
    "1": "understand",
    "2": "prove",
    "3": "construct",
}


class BlotIntegrationError(RuntimeError):
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
        raise BlotIntegrationError(
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
class RuntimeConfiguration:
    projection_profiles: tuple[
        ProjectionProfile,
        ...
    ]
    selection_policy: SelectionPolicy | None = None

    def normalized(self) -> dict[str, Any]:
        body = {
            "schema":
                f"{schema}.runtime-configuration",

            "projection_profiles":
                [
                    profile.normalized()
                    for profile
                    in self.projection_profiles
                ],

            "selection_policy":
                (
                    self.selection_policy
                    .normalized()
                    if self.selection_policy
                    is not None
                    else None
                ),

            "provider_routing_owner":
                "opus",

            "provider_execution_owner":
                "opus",

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


class BlotReconstructionRuntime:
    def __init__(
        self,
        *,
        opus_adapter: OpusAIAdapter | None = None,
        selection_policy: SelectionPolicy | None = None,
        projection_profiles: Iterable[
            ProjectionProfile
        ] | None = None,
    ) -> None:
        self.opus_adapter = (
            opus_adapter
            or OpusAIAdapter()
        )

        profiles = tuple(
            projection_profiles
            if projection_profiles
            is not None
            else default_projection_profiles()
        )

        if not profiles:
            raise BlotIntegrationError(
                "at least one projection "
                "profile is required"
            )

        self.configuration = (
            RuntimeConfiguration(
                projection_profiles=profiles,
                selection_policy=(
                    selection_policy
                ),
            )
        )

    def pipeline(
        self,
        source_digest: str,
        *,
        source_kind: str = "raster",
        objective: str | None = None,
        constraints: Mapping[
            str,
            Any
        ] | None = None,
        provenance: Iterable[str] = (),
    ) -> BlotPipeline:
        source_digest = _text(
            source_digest,
            "source_digest",
        )

        if objective is None:
            request = ReconstructionRequest(
                source_digest=source_digest,
                source_kind=source_kind,
                constraints=dict(
                    constraints
                    or {}
                ),
                provenance=tuple(
                    provenance
                ),
            )
        else:
            request = ReconstructionRequest(
                source_digest=source_digest,
                source_kind=source_kind,
                objective=_text(
                    objective,
                    "objective",
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
            opus_adapter=self.opus_adapter,
            selection_policy=(
                self.configuration
                .selection_policy
            ),
            projection_profiles=(
                self.configuration
                .projection_profiles
            ),
        )

    def status(
        self,
    ) -> dict[str, Any]:
        opus_status = (
            self.opus_adapter.status()
        )

        body = {
            "schema":
                f"{schema}.runtime-status",

            "name":
                name,

            "owner":
                owner,

            "orchestrator":
                orchestrator,

            "configuration":
                self.configuration
                .normalized(),

            "opus":
                opus_status,

            "provider_routing_owner":
                opus_status.get(
                    "routing_owner",
                    "opus",
                ),

            "provider_execution_owner":
                opus_status.get(
                    "execution_owner",
                    "opus",
                ),

            "blot_executes_providers":
                False,

            "blot_routes_providers":
                False,

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


def reconstruction_runtime(
    *,
    opus_adapter: OpusAIAdapter | None = None,
    selection_policy: SelectionPolicy | None = None,
    projection_profiles: Iterable[
        ProjectionProfile
    ] | None = None,
) -> BlotReconstructionRuntime:
    return BlotReconstructionRuntime(
        opus_adapter=opus_adapter,
        selection_policy=selection_policy,
        projection_profiles=projection_profiles,
    )


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
    selection_policy: SelectionPolicy | None = None,
    projection_profiles: Iterable[
        ProjectionProfile
    ] | None = None,
) -> BlotPipeline:
    runtime = reconstruction_runtime(
        opus_adapter=opus_adapter,
        selection_policy=selection_policy,
        projection_profiles=projection_profiles,
    )

    return runtime.pipeline(
        source_digest,
        source_kind=source_kind,
        objective=objective,
        constraints=constraints,
        provenance=provenance,
    )


def integration_manifest(
) -> dict[str, Any]:
    profiles = (
        default_projection_profiles()
    )

    body = {
        "schema":
            schema,

        "name":
            name,

        "owner":
            owner,

        "orchestrator":
            orchestrator,

        "authority_effect":
            authority_effect,

        "mutation_effect":
            mutation_effect,

        "projection_only":
            projection_only,

        "authoritative":
            False,

        "rungs":
            dict(
                rungs
            ),

        "stage_counts": {
            "understand": 32,
            "prove": 28,
            "construct": 32,
            "total": 92,
        },

        "representations": {
            "evidence":
                "observed raster evidence "
                "with confidence and provenance",

            "construction":
                "semantic construction graph",

            "projection":
                "deterministically derived svg",
        },

        "instance_first":
            True,

        "typed_segues":
            True,

        "substance_policy":
            (
                "substantiate once -> instance "
                "-> compose -> relate through "
                "typed segues -> project"
            ),

        "geometry_policy":
            (
                "geometry owns shape; materials "
                "decorate geometry"
            ),

        "svg_policy":
            (
                "svg is a deterministic projection "
                "of the construction graph"
            ),

        "provider_boundary": {
            "selection":
                "opus",

            "routing":
                "opus",

            "execution":
                "opus",

            "retries":
                "opus",

            "fallback":
                "opus",

            "cost_policy":
                "opus",

            "latency_policy":
                "opus",

            "adapter":
                "runtime.opus_ai_adapter."
                "OpusAIAdapter",

            "blot_owns_provider_policy":
                False,
        },

        "counterfactual_scope":
            (
                "construction strategy only; "
                "never provider routing"
            ),

        "hard_gate": {
            "rung_3_requires":
                "execution_ready=true",

            "unresolved_routes_to":
                "earliest relevant rung-1 stage",
        },

        "verification_lock":
            True,

        "verification_sequence": [
            "render",
            "measure",
            "compare",
            "accept-or-reject",
        ],

        "verification_dimensions": [
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
        ],

        "failure_policy":
            "route to earliest causal stage",

        "projection_profiles":
            [
                profile.profile_id
                for profile in profiles
            ],

        "lineage_preserved":
            True,

        "provenance_preserved":
            True,

        "deterministic_replay":
            True,

        "projection_is_authority":
            False,

        "canonical_substance_reconstructed_from_projection":
            False,
    }

    body[
        "digest"
    ] = _digest(
        body
    )

    return body


def selftest(
) -> dict[str, Any]:
    manifest_a = (
        integration_manifest()
    )

    manifest_b = (
        integration_manifest()
    )

    runtime = (
        reconstruction_runtime()
    )

    pipeline_a = runtime.pipeline(
        "verification-source",
        provenance=(
            "selftest",
        ),
    )

    pipeline_b = runtime.pipeline(
        "verification-source",
        provenance=(
            "selftest",
        ),
    )

    pipeline_manifest_a = (
        pipeline_a.manifest()
    )

    pipeline_manifest_b = (
        pipeline_b.manifest()
    )

    status_a = (
        runtime.status()
    )

    status_b = (
        runtime.status()
    )

    checks = {
        "name_exact":
            name
            == "blot.",

        "owner_exact":
            owner
            == "blot.",

        "orchestrator_exact":
            orchestrator
            == "opus",

        "authority_none":
            authority_effect
            == "none",

        "mutation_none":
            mutation_effect
            == "none",

        "projection_only":
            projection_only
            is True,

        "non_authoritative":
            manifest_a[
                "authoritative"
            ]
            is False,

        "three_rungs":
            manifest_a[
                "rungs"
            ]
            == {
                "1": "understand",
                "2": "prove",
                "3": "construct",
            },

        "ninety_two_stages":
            manifest_a[
                "stage_counts"
            ][
                "total"
            ]
            == 92,

        "instance_first":
            manifest_a[
                "instance_first"
            ]
            is True,

        "typed_segues":
            manifest_a[
                "typed_segues"
            ]
            is True,

        "verification_lock":
            manifest_a[
                "verification_lock"
            ]
            is True,

        "opus_selects":
            manifest_a[
                "provider_boundary"
            ][
                "selection"
            ]
            == "opus",

        "opus_routes":
            manifest_a[
                "provider_boundary"
            ][
                "routing"
            ]
            == "opus",

        "opus_executes":
            manifest_a[
                "provider_boundary"
            ][
                "execution"
            ]
            == "opus",

        "blot_no_provider_policy":
            manifest_a[
                "provider_boundary"
            ][
                "blot_owns_provider_policy"
            ]
            is False,

        "svg_derived":
            pipeline_manifest_a[
                "projection"
            ][
                "svg_is_derived"
            ]
            is True,

        "construction_owner":
            pipeline_manifest_a[
                "construction"
            ][
                "owner"
            ]
            == "blot.",

        "orchestration_owner":
            pipeline_manifest_a[
                "orchestration"
            ][
                "owner"
            ]
            == "opus",

        "runtime_no_provider_execution":
            status_a[
                "blot_executes_providers"
            ]
            is False,

        "runtime_no_provider_routing":
            status_a[
                "blot_routes_providers"
            ]
            is False,

        "deterministic_manifest":
            manifest_a
            == manifest_b,

        "deterministic_pipeline":
            pipeline_manifest_a
            == pipeline_manifest_b,

        "deterministic_runtime_status":
            status_a
            == status_b,
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

        "integration_digest":
            manifest_a[
                "digest"
            ],

        "pipeline_digest":
            pipeline_manifest_a[
                "digest"
            ],

        "runtime_digest":
            status_a[
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
    "BlotIntegrationError",
    "BlotReconstructionRuntime",
    "RuntimeConfiguration",
    "authority_effect",
    "integration_manifest",
    "mutation_effect",
    "name",
    "orchestrator",
    "owner",
    "projection_only",
    "reconstruction_pipeline",
    "reconstruction_runtime",
    "rungs",
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
