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

from .blot import (
    blot_renderer,
    manifest as blot_manifest,
    register_blot_renderer,
    selftest as blot_selftest,
)


register_blot_renderer(
    svg_runtime,
    replace=True,
)


__all__ = [
    "NS",
    "SVG_NS",
    "TL_NS",
    "RendererBackend",
    "SVGLimits",
    "TranslucentSVGError",
    "TranslucentSVGRuntime",
    "blot_manifest",
    "blot_renderer",
    "blot_selftest",
    "register_blot_renderer",
    "register_renderer",
    "selftest",
    "svg_manifest",
    "svg_runtime",
]
