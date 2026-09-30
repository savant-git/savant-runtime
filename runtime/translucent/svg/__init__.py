#!/usr/bin/env python3

from __future__ import annotations

from .runtime import (
    NS,
    SVG_NS,
    TL_NS,
    RendererBackend,
    SVGLimits,
    TranslucentSVGError,
    TranslucentSVGRuntime,
    register_renderer,
    selftest,
    svg_manifest,
    svg_runtime,
)


schema = "savant.translucent.svg.package.v1"
owner = "savant"
authority_effect = "none"


def manifest() -> dict[str, object]:
    return {
        "schema": schema,
        "owner": owner,
        "kind": "translucent-svg-runtime-package",
        "runtime_schema": svg_manifest()["schema"],
        "renderers": svg_runtime.renderer_names(),
        "authority_effect": authority_effect,
        "projection_only": True,
        "authoritative": False,
    }


__all__ = [
    "NS",
    "SVG_NS",
    "TL_NS",
    "RendererBackend",
    "SVGLimits",
    "TranslucentSVGError",
    "TranslucentSVGRuntime",
    "authority_effect",
    "manifest",
    "owner",
    "register_renderer",
    "schema",
    "selftest",
    "svg_manifest",
    "svg_runtime",
]
