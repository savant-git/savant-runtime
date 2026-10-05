#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


schema_version = (
    "savant.assurance."
    "atlas-niche-integration-check.v1"
)

authority_effect = "none"

runtime_root = Path(
    "/root/savant-runtime"
)

niche_root = Path(
    "/root/savant-runtime"
    "/ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche"
)

taskboard_root = (
    niche_root
    / "apps"
    / "taskboard"
)

atlas_root = (
    niche_root
    / "apps"
    / "atlas"
)

server_path = (
    taskboard_root
    / "server.py"
)

adapter_path = (
    taskboard_root
    / "atlas_adapter.py"
)

atlas_projection_path = (
    atlas_root
    / "atlas_projection.py"
)

atlas_index_path = (
    atlas_root
    / "assets"
    / "index.html"
)

atlas_css_path = (
    atlas_root
    / "assets"
    / "atlas.css"
)

atlas_js_path = (
    atlas_root
    / "assets"
    / "atlas.js"
)

navigation_js_path = (
    taskboard_root
    / "assets"
    / "niche-navigation.js"
)

navigation_css_path = (
    taskboard_root
    / "assets"
    / "niche-navigation.css"
)


class IntegrationError(
    RuntimeError
):
    pass


def read_text(
    path: Path,
) -> str:
    if not path.is_file():
        raise IntegrationError(
            f"required file unavailable: {path}"
        )

    return path.read_text(
        encoding="utf-8"
    )


def load_module(
    name: str,
    path: Path,
):
    specification = (
        importlib.util.spec_from_file_location(
            name,
            path,
        )
    )

    if (
        specification is None
        or specification.loader is None
    ):
        raise IntegrationError(
            f"cannot load module: {path}"
        )

    module = (
        importlib.util.module_from_spec(
            specification
        )
    )

    sys.modules[
        name
    ] = module

    specification.loader.exec_module(
        module
    )

    return module


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise IntegrationError(
            message
        )


def check_server() -> dict[str, Any]:
    text = read_text(
        server_path
    )

    compile(
        text,
        str(
            server_path
        ),
        "exec",
    )

    require(
        "try_handle_atlas_get(self)"
        in text,
        "taskboard GET handler does not delegate to Atlas",
    )

    require(
        "reject_atlas_mutation(self)"
        in text,
        "taskboard mutation boundary does not protect Atlas",
    )

    require(
        "try_handle_get as try_handle_atlas_get"
        in text,
        "Atlas adapter import missing",
    )

    return {
        "status":
            "passed",
        "path":
            str(
                server_path
            ),
    }


def check_adapter() -> dict[str, Any]:
    module = load_module(
        "savant_niche_atlas_adapter_check",
        adapter_path,
    )

    require(
        getattr(
            module,
            "authority_effect",
            None,
        )
        == "none",
        "Atlas adapter authority effect is not none",
    )

    require(
        getattr(
            module,
            "projection_only",
            None,
        )
        is True,
        "Atlas adapter is not projection-only",
    )

    require(
        getattr(
            module,
            "mutation_authority",
            None,
        )
        is False,
        "Atlas adapter exposes mutation authority",
    )

    expected_paths = (
        "/atlas",
        "/atlas/",
        "/atlas/index.html",
        "/atlas/assets/atlas.css",
        "/atlas/assets/atlas.js",
        "/api/atlas",
        "/api/atlas/summary",
        "/api/atlas/self-check",
        "/api/atlas/health",
    )

    missing = [
        path
        for path
        in expected_paths
        if not module.handles_path(
            path
        )
    ]

    require(
        not missing,
        "Atlas adapter route coverage missing: "
        + ", ".join(
            missing
        ),
    )

    return {
        "status":
            "passed",
        "path":
            str(
                adapter_path
            ),
        "routes_checked":
            list(
                expected_paths
            ),
    }


def check_projection() -> dict[str, Any]:
    module = load_module(
        "savant_niche_atlas_projection_check",
        atlas_projection_path,
    )

    require(
        getattr(
            module,
            "authority_effect",
            None,
        )
        == "none",
        "Atlas projection authority effect is not none",
    )

    require(
        getattr(
            module,
            "projection_only",
            None,
        )
        is True,
        "Atlas projection is not projection-only",
    )

    require(
        getattr(
            module,
            "mutation_authority",
            None,
        )
        is False,
        "Atlas projection exposes mutation authority",
    )

    projection = (
        module.atlas_projection()
    )

    require(
        isinstance(
            projection,
            dict,
        ),
        "Atlas projection did not return an object",
    )

    require(
        projection.get(
            "projection_only"
        )
        is True,
        "Atlas projection result lost projection-only boundary",
    )

    require(
        projection.get(
            "mutation_authority"
        )
        is False,
        "Atlas projection result acquired mutation authority",
    )

    nodes = projection.get(
        "nodes"
    )

    edges = projection.get(
        "edges"
    )

    require(
        isinstance(
            nodes,
            list,
        ),
        "Atlas projection nodes are unavailable",
    )

    require(
        isinstance(
            edges,
            list,
        ),
        "Atlas projection edges are unavailable",
    )

    return {
        "status":
            "passed",
        "path":
            str(
                atlas_projection_path
            ),
        "node_count":
            len(
                nodes
            ),
        "edge_count":
            len(
                edges
            ),
    }


def check_frontend() -> dict[str, Any]:
    index_text = read_text(
        atlas_index_path
    )

    css_text = read_text(
        atlas_css_path
    )

    js_text = read_text(
        atlas_js_path
    )

    require(
        'href="/atlas/assets/atlas.css"'
        in index_text,
        "Atlas stylesheet route is incorrect",
    )

    require(
        'src="/atlas/assets/atlas.js"'
        in index_text,
        "Atlas JavaScript route is incorrect",
    )

    require(
        'id="atlas-canvas"'
        in index_text,
        "Atlas map canvas unavailable",
    )

    require(
        'id="atlas-minimap"'
        in index_text,
        "Atlas minimap unavailable",
    )

    require(
        'id="atlas-inspector"'
        in index_text,
        "Atlas inspector unavailable",
    )

    require(
        'id="atlas-search"'
        in index_text,
        "Atlas search surface unavailable",
    )

    require(
        'fetch("/api/atlas"'
        in js_text,
        "Atlas frontend does not consume Niche Atlas projection",
    )

    require(
        "state.dependencyTrace"
        in js_text,
        "Atlas dependency trace unavailable",
    )

    require(
        "semanticZoom"
        in js_text,
        "Atlas semantic zoom unavailable",
    )

    require(
        "rebuildSpatialIndex"
        in js_text,
        "Atlas spatial index unavailable",
    )

    require(
        "drawMinimap"
        in js_text,
        "Atlas minimap renderer unavailable",
    )

    require(
        "prefers-reduced-motion"
        in css_text,
        "Atlas reduced-motion support unavailable",
    )

    require(
        "prefers-contrast"
        in css_text,
        "Atlas high-contrast support unavailable",
    )

    return {
        "status":
            "passed",
        "index":
            str(
                atlas_index_path
            ),
        "css":
            str(
                atlas_css_path
            ),
        "javascript":
            str(
                atlas_js_path
            ),
    }


def check_navigation() -> dict[str, Any]:
    javascript = read_text(
        navigation_js_path
    )

    stylesheet = read_text(
        navigation_css_path
    )

    require(
        'const atlasRoute =\n        "/atlas/";'
        in javascript,
        "Niche Atlas navigation route unavailable",
    )

    require(
        'data-savant-surface="atlas"'
        in stylesheet,
        "Niche Atlas navigation style unavailable",
    )

    require(
        'window.location.assign(\n            atlasRoute'
        in javascript,
        "Niche Atlas navigation activation unavailable",
    )

    return {
        "status":
            "passed",
        "javascript":
            str(
                navigation_js_path
            ),
        "css":
            str(
                navigation_css_path
            ),
    }


def main() -> int:
    checks: dict[
        str,
        Any,
    ] = {}

    try:
        checks[
            "server"
        ] = check_server()

        checks[
            "adapter"
        ] = check_adapter()

        checks[
            "projection"
        ] = check_projection()

        checks[
            "frontend"
        ] = check_frontend()

        checks[
            "navigation"
        ] = check_navigation()

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema_version,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "failed",
                    "owner":
                        "exile:niche",
                    "projection_only":
                        True,
                    "mutation_authority":
                        False,
                    "checks":
                        checks,
                    "error":
                        str(
                            exc
                        ),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            {
                "schema":
                    schema_version,
                "authority_effect":
                    authority_effect,
                "status":
                    "passed",
                "owner":
                    "exile:niche",
                "projection_only":
                    True,
                "mutation_authority":
                    False,
                "surface":
                    "atlas",
                "route":
                    "/atlas/",
                "checks":
                    checks,
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
