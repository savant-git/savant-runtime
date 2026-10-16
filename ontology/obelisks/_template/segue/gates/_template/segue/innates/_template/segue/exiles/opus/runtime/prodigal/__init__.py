from __future__ import annotations

from typing import Any, Iterable, Mapping

from .composition import project as project_composition


__all__ = [
    "project",
    "project_composition",
]


def project(
    *,
    route: Mapping[str, Any],
    providers: Iterable[Mapping[str, Any]],
    required_capabilities: Iterable[Any] | None = None,
    required_layers: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """
    Public aperture for recovered Opus Prodigal projections.

    Projection only. Provider selection, availability, policy binding,
    model suitability, provider loading, and execution remain owned by
    opus.runtime.router.
    """

    return project_composition(
        route=route,
        providers=providers,
        required_capabilities=required_capabilities,
        required_layers=required_layers,
    )
