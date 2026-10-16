#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from runtime.translucent.blot_opus import (
    ProviderCapability,
    SelectionPolicy,
)
from runtime.translucent.blot_pipeline import (
    BlotPipeline,
    ProjectionProfile,
    ReconstructionRequest,
    default_projection_profiles,
)


name = "blot."
schema = "savant.translucent.blot.integration.v1"
authority_effect = "none"
projection_only = True


class BlotIntegrationError(ValueError):
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
        raise BlotIntegrationError(
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
class BlotReconstructionOptions:
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

        return {
            "preferred_providers":
                list(
                    _unique(
                        self.preferred_providers
                    )
                ),

            "projection_profiles":
                [
                    profile.normalized()
                    for profile in profiles
                ],

            "metadata":
                dict(
                    self.metadata
                    or {}
                ),
        }


class BlotReconstructionRuntime:
    def __init__(
        self,
        *,
        providers: Iterable[
            ProviderCapability
        ] = (),
        selection_policy: SelectionPolicy | None = None,
    ) -> None:
        self._providers = tuple(
            providers
        )

        self._selection_policy = (
            selection_policy
        )

    @property
    def providers(
        self,
    ) -> tuple[
        ProviderCapability,
        ...
    ]:
        return self._providers

    def pipeline(
        self,
        source_digest: str,
        *,
        options: BlotReconstructionOptions | None = None,
    ) -> BlotPipeline:
        source_digest = _text(
            source_digest,
            "source_digest",
        )

        options = (
            options
            if options is not None
            else BlotReconstructionOptions()
        )

        normalized = options.normalized()

        profiles = tuple(
            ProjectionProfile(
                profile_id=profile[
                    "profile_id"
                ],
                width=profile[
                    "width"
                ],
                height=profile[
                    "height"
                ],
                mode=profile[
                    "mode"
                ],
                detail=profile[
                    "detail"
                ],
                color=profile[
                    "color"
                ],
                effects=profile[
                    "effects"
                ],
            )
            for profile
            in normalized[
                "projection_profiles"
            ]
        )

        request = ReconstructionRequest(
            source_digest=source_digest,
            preferred_providers=tuple(
                normalized[
                    "preferred_providers"
                ]
            ),
            projection_profiles=profiles,
            metadata=normalized[
                "metadata"
            ],
        )

        return BlotPipeline(
            request,
            providers=self._providers,
            selection_policy=(
                self._selection_policy
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

            "owner":
                "blot.",

            "orchestrator":
                "opus",

            "rungs":
                {
                    "1":
                        "understand",

                    "2":
                        "prove",

                    "3":
                        "construct",
                },

            "verification_lock":
                True,

            "substantiate_once":
                True,

            "instance_first":
                True,

            "typed_segues":
                True,

            "deterministic_projection":
                True,

            "lineage":
                True,

            "provenance":
                True,

            "replay":
                True,

            "provider_neutral":
                True,

            "projection_profiles":
                [
                    profile.normalized()
                    for profile
                    in default_projection_profiles()
                ],

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


def reconstruction_runtime(
    *,
    providers: Iterable[
        ProviderCapability
    ] = (),
    selection_policy: SelectionPolicy | None = None,
) -> BlotReconstructionRuntime:
    return BlotReconstructionRuntime(
        providers=providers,
        selection_policy=selection_policy,
    )


def reconstruction_pipeline(
    source_digest: str,
    *,
    providers: Iterable[
        ProviderCapability
    ] = (),
    preferred_providers: Iterable[str] = (),
    projection_profiles: Iterable[
        ProjectionProfile
    ] = (),
    metadata: Mapping[str, Any] | None = None,
    selection_policy: SelectionPolicy | None = None,
) -> BlotPipeline:
    runtime = reconstruction_runtime(
        providers=providers,
        selection_policy=selection_policy,
    )

    return runtime.pipeline(
        source_digest,
        options=BlotReconstructionOptions(
            preferred_providers=tuple(
                preferred_providers
            ),
            projection_profiles=tuple(
                projection_profiles
            ),
            metadata=metadata,
        ),
    )


def integration_manifest(
) -> dict[str, Any]:
    return reconstruction_runtime().manifest()


def selftest(
) -> dict[str, Any]:
    provider = ProviderCapability(
        provider_id="local",
        capabilities=(
            "*",
        ),
        deterministic=True,
        local=True,
        priority=1,
    )

    runtime = reconstruction_runtime(
        providers=(
            provider,
        )
    )

    pipeline_a = runtime.pipeline(
        "integration-source",
        options=BlotReconstructionOptions(
            preferred_providers=(
                "local",
            ),
        ),
    )

    pipeline_b = runtime.pipeline(
        "integration-source",
        options=BlotReconstructionOptions(
            preferred_providers=(
                "local",
            ),
        ),
    )

    manifest_a = runtime.manifest()
    manifest_b = runtime.manifest()

    pipeline_manifest_a = (
        pipeline_a.manifest()
    )

    pipeline_manifest_b = (
        pipeline_b.manifest()
    )

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

        "owner":
            manifest_a[
                "owner"
            ]
            == "blot.",

        "opus_orchestrator":
            manifest_a[
                "orchestrator"
            ]
            == "opus",

        "three_rungs":
            manifest_a[
                "rungs"
            ]
            == {
                "1":
                    "understand",

                "2":
                    "prove",

                "3":
                    "construct",
            },

        "verification_lock":
            manifest_a[
                "verification_lock"
            ]
            is True,

        "typed_segues":
            manifest_a[
                "typed_segues"
            ]
            is True,

        "instance_first":
            manifest_a[
                "instance_first"
            ]
            is True,

        "deterministic_manifest":
            manifest_a
            == manifest_b,

        "deterministic_pipeline":
            pipeline_manifest_a
            == pipeline_manifest_b,

        "source_preserved":
            pipeline_a.request_data[
                "source_digest"
            ]
            == "integration-source",

        "provider_preserved":
            pipeline_a.request_data[
                "preferred_providers"
            ]
            == [
                "local"
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

        "manifest_digest":
            manifest_a[
                "digest"
            ],

        "pipeline_manifest_digest":
            pipeline_manifest_a[
                "digest"
            ],
    }


__all__ = [
    "BlotIntegrationError",
    "BlotReconstructionOptions",
    "BlotReconstructionRuntime",
    "authority_effect",
    "integration_manifest",
    "name",
    "projection_only",
    "reconstruction_pipeline",
    "reconstruction_runtime",
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
