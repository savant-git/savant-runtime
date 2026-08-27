from __future__ import annotations

from typing import Any, Dict

from projectors.docs_view import project_docs
from projectors.graph_view import project_graph
from projectors.coalesce_view import derive_coalesce_view


def project(
    root: str,
    view: str = "graph",
    **options: Any,
) -> Dict[str, Any]:
    if view == "graph":
        return project_graph(
            root
        )

    if view == "docs":
        return project_docs(
            root
        )

    if view == "coalesce":
        recipe = str(
            options.get(
                "recipe",
                "chronology-explorer",
            )
        )

        context = options.get(
            "context",
            {},
        )

        if not isinstance(
            context,
            dict,
        ):
            raise TypeError(
                "Coalesce context must be an object."
            )

        return derive_coalesce_view(
            recipe,
            context,
        )

    raise ValueError(
        (
            "unsupported Filament "
            f"wavre view: {view}"
        )
    )
