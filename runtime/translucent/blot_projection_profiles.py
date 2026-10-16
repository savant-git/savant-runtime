#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


name = "blot."
schema = "savant.translucent.blot.projection-profiles.v1"
authority_effect = "none"
mutation_effect = "none"
projection_only = True

max_profiles = 32


class BlotProjectionProfileError(ValueError):
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
        raise BlotProjectionProfileError(
            "value is not canonical-json compatible"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical(value).encode("utf-8")
    ).hexdigest()


def _text(value: Any, field_name: str) -> str:
    result = str(value or "").strip()

    if not result:
        raise BlotProjectionProfileError(
            f"{field_name} is required"
        )

    return result


def _unique(
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
class ProjectionProfile:
    profile_id: str
    purpose: str
    geometry_mode: str
    material_mode: str
    lighting_mode: str
    detail_mode: str
    preserve_negative_space: bool = True
    preserve_topology: bool = True
    preserve_lineage: bool = True
    preserve_provenance: bool = True
    constraints: Mapping[str, Any] = field(
        default_factory=dict
    )

    def normalized(self) -> dict[str, Any]:
        geometry_mode = _text(
            self.geometry_mode,
            "geometry_mode",
        )

        material_mode = _text(
            self.material_mode,
            "material_mode",
        )

        lighting_mode = _text(
            self.lighting_mode,
            "lighting_mode",
        )

        detail_mode = _text(
            self.detail_mode,
            "detail_mode",
        )

        allowed_geometry = {
            "canonical",
            "simplified",
            "micro-optimized",
        }

        allowed_material = {
            "canonical",
            "flat",
            "monochrome",
            "reduced",
        }

        allowed_lighting = {
            "canonical",
            "reduced",
            "none",
        }

        allowed_detail = {
            "full",
            "standard",
            "reduced",
            "micro",
        }

        if geometry_mode not in allowed_geometry:
            raise BlotProjectionProfileError(
                f"unsupported geometry_mode: {geometry_mode}"
            )

        if material_mode not in allowed_material:
            raise BlotProjectionProfileError(
                f"unsupported material_mode: {material_mode}"
            )

        if lighting_mode not in allowed_lighting:
            raise BlotProjectionProfileError(
                f"unsupported lighting_mode: {lighting_mode}"
            )

        if detail_mode not in allowed_detail:
            raise BlotProjectionProfileError(
                f"unsupported detail_mode: {detail_mode}"
            )

        body = {
            "profile_id": _text(
                self.profile_id,
                "profile_id",
            ),
            "purpose": _text(
                self.purpose,
                "purpose",
            ),
            "geometry_mode": geometry_mode,
            "material_mode": material_mode,
            "lighting_mode": lighting_mode,
            "detail_mode": detail_mode,
            "preserve_negative_space":
                bool(self.preserve_negative_space),
            "preserve_topology":
                bool(self.preserve_topology),
            "preserve_lineage":
                bool(self.preserve_lineage),
            "preserve_provenance":
                bool(self.preserve_provenance),
            "constraints": dict(
                self.constraints
            ),
        }

        if not body["preserve_topology"]:
            raise BlotProjectionProfileError(
                "projection profiles cannot disable topology preservation"
            )

        if not body["preserve_negative_space"]:
            raise BlotProjectionProfileError(
                "projection profiles cannot disable negative-space preservation"
            )

        if not body["preserve_lineage"]:
            raise BlotProjectionProfileError(
                "projection profiles cannot disable lineage preservation"
            )

        if not body["preserve_provenance"]:
            raise BlotProjectionProfileError(
                "projection profiles cannot disable provenance preservation"
            )

        return {
            **body,
            "digest": _digest(body),
        }


presentation = ProjectionProfile(
    profile_id="presentation",
    purpose="canonical presentation projection",
    geometry_mode="canonical",
    material_mode="canonical",
    lighting_mode="canonical",
    detail_mode="full",
)

standard = ProjectionProfile(
    profile_id="standard",
    purpose="general-purpose scalable projection",
    geometry_mode="canonical",
    material_mode="canonical",
    lighting_mode="reduced",
    detail_mode="standard",
)

flat = ProjectionProfile(
    profile_id="flat",
    purpose="flat vector projection",
    geometry_mode="canonical",
    material_mode="flat",
    lighting_mode="none",
    detail_mode="standard",
)

monochrome = ProjectionProfile(
    profile_id="monochrome",
    purpose="single-palette semantic projection",
    geometry_mode="canonical",
    material_mode="monochrome",
    lighting_mode="none",
    detail_mode="reduced",
)

micro = ProjectionProfile(
    profile_id="micro",
    purpose="small optical-size projection",
    geometry_mode="micro-optimized",
    material_mode="reduced",
    lighting_mode="none",
    detail_mode="micro",
    constraints={
        "optical_size": "micro",
        "prefer_anchor_reduction": True,
        "prefer_material_reduction": True,
        "preserve_primary_silhouette": True,
        "preserve_primary_negative_space": True,
    },
)


default_profiles = (
    presentation,
    standard,
    flat,
    monochrome,
    micro,
)


class ProjectionProfileRegistry:
    def __init__(
        self,
        profiles: Iterable[
            ProjectionProfile
        ] = default_profiles,
    ) -> None:
        self._profiles: dict[
            str,
            ProjectionProfile,
        ] = {}

        for profile in profiles:
            self.register(profile)

    def register(
        self,
        profile: ProjectionProfile,
    ) -> ProjectionProfile:
        if not isinstance(
            profile,
            ProjectionProfile,
        ):
            raise BlotProjectionProfileError(
                "profile must be ProjectionProfile"
            )

        if len(self._profiles) >= max_profiles:
            raise BlotProjectionProfileError(
                "projection profile limit exceeded"
            )

        normalized = profile.normalized()
        profile_id = normalized["profile_id"]

        existing = self._profiles.get(
            profile_id
        )

        if existing is not None:
            if (
                existing.normalized()["digest"]
                != normalized["digest"]
            ):
                raise BlotProjectionProfileError(
                    "projection profile identity conflict"
                )

            return existing

        self._profiles[
            profile_id
        ] = profile

        return profile

    def get(
        self,
        profile_id: str,
    ) -> ProjectionProfile:
        profile_id = _text(
            profile_id,
            "profile_id",
        )

        try:
            return self._profiles[
                profile_id
            ]
        except KeyError as exc:
            raise BlotProjectionProfileError(
                f"unknown projection profile: {profile_id}"
            ) from exc

    def profiles(
        self,
    ) -> tuple[ProjectionProfile, ...]:
        return tuple(
            self._profiles[key]
            for key in sorted(
                self._profiles
            )
        )

    def manifest(
        self,
    ) -> dict[str, Any]:
        profiles = [
            profile.normalized()
            for profile
            in self.profiles()
        ]

        body = {
            "schema": schema,
            "name": name,
            "authority_effect": authority_effect,
            "mutation_effect": mutation_effect,
            "projection_only": projection_only,
            "profile_count": len(profiles),
            "profiles": profiles,
            "canonical_construction_unchanged": True,
            "projection_is_authority": False,
        }

        return {
            **body,
            "digest": _digest(body),
        }


def manifest() -> dict[str, Any]:
    registry = ProjectionProfileRegistry()

    body = {
        "schema": schema,
        "name": name,
        "authority_effect": authority_effect,
        "mutation_effect": mutation_effect,
        "projection_only": projection_only,
        "default_profile_ids": [
            profile.profile_id
            for profile
            in default_profiles
        ],
        "default_profile_digest":
            registry.manifest()["digest"],
        "canonical_construction_unchanged": True,
        "projection_is_authority": False,
        "profile_semantics":
            "deterministic-derived-view",
    }

    return {
        **body,
        "digest": _digest(body),
    }


__all__ = [
    "BlotProjectionProfileError",
    "ProjectionProfile",
    "ProjectionProfileRegistry",
    "authority_effect",
    "default_profiles",
    "flat",
    "manifest",
    "max_profiles",
    "micro",
    "monochrome",
    "mutation_effect",
    "name",
    "presentation",
    "projection_only",
    "schema",
    "standard",
]


if __name__ == "__main__":
    print(
        json.dumps(
            manifest(),
            indent=2,
            sort_keys=True,
        )
    )
