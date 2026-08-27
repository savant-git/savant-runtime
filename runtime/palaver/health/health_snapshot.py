#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping
import urllib.request


ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).expanduser().absolute()

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from runtime.lineage.model import stable_hash  # noqa: E402


OUT = (
    ROOT
    / "vault"
    / "health"
    / "palaver_health_snapshot.json"
)


ARTIFACTS = {
    "lineage": (
        ROOT
        / "vault"
        / "lineage"
        / "functional_lineage_graph.json"
    ),
    "runtime": (
        ROOT
        / "vault"
        / "graphs"
        / "runtime_graph.json"
    ),
    "fields": (
        ROOT
        / "vault"
        / "fields"
        / "structural_fields.json"
    ),
    "topology": (
        ROOT
        / "vault"
        / "graphs"
        / "topology_projection.json"
    ),
    "authority": (
        ROOT
        / "vault"
        / "authority"
        / "authority_index.json"
    ),
    "registry": (
        ROOT
        / "vault"
        / "registry"
        / "observatory_registry.json"
    ),
}


PROGRAM_FILES = {
    "lineage_engine": (
        ROOT
        / "runtime"
        / "palaver"
        / "lineage"
        / "lineage_engine.py"
    ),
    "runtime_graph_engine": (
        ROOT
        / "runtime"
        / "palaver"
        / "graph"
        / "runtime_graph_engine.py"
    ),
    "runtime_graph_index": (
        ROOT
        / "runtime"
        / "palaver"
        / "graph"
        / "runtime_graph_index.py"
    ),
    "structural_fields": (
        ROOT
        / "runtime"
        / "palaver"
        / "fields"
        / "structural_fields.py"
    ),
    "topology_compiler": (
        ROOT
        / "runtime"
        / "palaver"
        / "topology"
        / "topology_compiler.py"
    ),
    "authority_engine": (
        ROOT
        / "runtime"
        / "palaver"
        / "authority"
        / "authority_engine.py"
    ),
    "search_fabric": (
        ROOT
        / "runtime"
        / "palaver"
        / "search"
        / "search_fabric.py"
    ),
    "investigation_builder": (
        ROOT
        / "runtime"
        / "palaver"
        / "investigation"
        / "investigation_packet_builder.py"
    ),
}


API_PATHS = (
    "/api/graph",
    "/api/observatory/authority",
    "/api/observatory/lineage",
    "/api/observatory/fields",
    "/api/observatory/topology",
    "/api/observatory/search?q=palaver",
)


def _read_artifact(
    path: Path,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "path": str(
            path
        ),
        "exists": path.is_file(),
        "readable": False,
        "schema": None,
        "deterministic_hash": None,
        "source_runtime_hash": None,
        "source_lineage_hash": None,
        "error": None,
    }

    if not path.is_file():
        return state

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        state[
            "error"
        ] = str(
            exc
        )

        return state

    if not isinstance(
        payload,
        Mapping,
    ):
        state[
            "error"
        ] = (
            "artifact root is not an object"
        )

        return state

    state[
        "readable"
    ] = True

    for key in (
        "schema",
        "deterministic_hash",
        "source_runtime_hash",
        "source_lineage_hash",
    ):
        state[
            key
        ] = payload.get(
            key
        )

    state[
        "payload"
    ] = dict(
        payload
    )

    return state


def _api_checks(
    base_url: str,
    timeout: float,
) -> dict[str, Any]:
    result: dict[
        str,
        Any,
    ] = {}

    for path in API_PATHS:
        url = (
            base_url.rstrip(
                "/"
            )
            + path
        )

        try:
            with urllib.request.urlopen(
                url,
                timeout=timeout,
            ) as response:
                result[
                    path
                ] = {
                    "ok": True,
                    "status": (
                        response.status
                    ),
                    "sample": (
                        response
                        .read(
                            240
                        )
                        .decode(
                            "utf-8",
                            errors="replace",
                        )
                    ),
                }

        except Exception as exc:
            result[
                path
            ] = {
                "ok": False,
                "error": repr(
                    exc
                ),
            }

    return result


def compile_health(
    *,
    include_api: bool = False,
    base_url: str = (
        "http://127.0.0.1:8787"
    ),
    timeout: float = 4.0,
) -> dict[str, Any]:
    program_checks = {
        name: path.is_file()
        for name, path
        in PROGRAM_FILES.items()
    }

    artifacts = {
        name: _read_artifact(
            path
        )
        for name, path
        in ARTIFACTS.items()
    }

    lineage = artifacts[
        "lineage"
    ]

    runtime = artifacts[
        "runtime"
    ]

    fields = artifacts[
        "fields"
    ]

    topology = artifacts[
        "topology"
    ]

    authority = artifacts[
        "authority"
    ]

    lineage_hash = lineage.get(
        "deterministic_hash"
    )

    runtime_hash = runtime.get(
        "deterministic_hash"
    )

    projection_checks = {
        "runtime_descends_from_lineage": (
            bool(
                lineage_hash
            )
            and runtime.get(
                "source_lineage_hash"
            )
            == lineage_hash
        ),
        "fields_descend_from_runtime": (
            bool(
                runtime_hash
            )
            and fields.get(
                "source_runtime_hash"
            )
            == runtime_hash
        ),
        "topology_descends_from_runtime": (
            bool(
                runtime_hash
            )
            and topology.get(
                "source_runtime_hash"
            )
            == runtime_hash
        ),
        "authority_descends_from_runtime": (
            bool(
                runtime_hash
            )
            and authority.get(
                "source_runtime_hash"
            )
            == runtime_hash
        ),
        "fields_expose_lineage": (
            bool(
                lineage_hash
            )
            and fields.get(
                "source_lineage_hash"
            )
            == lineage_hash
        ),
        "topology_exposes_lineage": (
            bool(
                lineage_hash
            )
            and topology.get(
                "source_lineage_hash"
            )
            == lineage_hash
        ),
        "authority_exposes_lineage": (
            bool(
                lineage_hash
            )
            and authority.get(
                "source_lineage_hash"
            )
            == lineage_hash
        ),
    }

    required_artifacts_ok = all(
        state[
            "exists"
        ]
        and state[
            "readable"
        ]
        for state in artifacts.values()
    )

    program_ok = all(
        program_checks.values()
    )

    projection_ok = all(
        projection_checks.values()
    )

    api = (
        _api_checks(
            base_url,
            timeout,
        )
        if include_api
        else {}
    )

    api_ok = (
        all(
            item.get(
                "ok",
                False,
            )
            for item in api.values()
        )
        if include_api
        else True
    )

    failures: list[str] = []

    if not program_ok:
        failures.append(
            "required program files missing"
        )

    if not required_artifacts_ok:
        failures.append(
            "required projections missing or unreadable"
        )

    if not projection_ok:
        failures.append(
            "projection lineage mismatch"
        )

    if not api_ok:
        failures.append(
            "one or more API checks failed"
        )

    status = (
        "healthy"
        if not failures
        else "degraded"
    )

    deterministic_core = {
        "schema": (
            "savant."
            "palaver_health.v2"
        ),
        "status": status,
        "program_checks": (
            program_checks
        ),
        "artifacts": {
            name: {
                key: value
                for key, value
                in state.items()
                if key != "payload"
            }
            for name, state
            in artifacts.items()
        },
        "projection_checks": (
            projection_checks
        ),
        "api": api,
        "failures": failures,
    }

    return {
        "schema": (
            "savant."
            "palaver_health.v2"
        ),
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "root": str(
            ROOT
        ),
        "status": status,
        "healthy": not failures,
        "deterministic_hash": stable_hash(
            deterministic_core
        ),
        "program_checks": (
            program_checks
        ),
        "artifacts": (
            deterministic_core[
                "artifacts"
            ]
        ),
        "projection_checks": (
            projection_checks
        ),
        "api": api,
        "failures": failures,
    }


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Palaver lineage, "
            "projection, authority, and "
            "observatory health."
        )
    )

    parser.add_argument(
        "--api",
        action="store_true",
    )

    parser.add_argument(
        "--base-url",
        default=(
            "http://127.0.0.1:8787"
        ),
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=4.0,
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    payload = compile_health(
        include_api=args.api,
        base_url=args.base_url,
        timeout=max(
            0.1,
            args.timeout,
        ),
    )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return (
        0
        if payload[
            "healthy"
        ]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
