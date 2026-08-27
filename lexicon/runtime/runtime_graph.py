#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(
    __file__
).resolve().parent

LEXICON_ROOT = ROOT.parent

REGISTRY = (
    ROOT
    / "runtime_registry.yaml"
)

DEFAULT_OUTPUT = (
    ROOT
    / "compiled"
)


class RuntimeGraphError(
    RuntimeError
):
    pass


def load_yaml(
    path: Path,
) -> dict[str, Any]:

    if not path.exists():

        raise FileNotFoundError(
            str(path)
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        data = yaml.safe_load(
            handle
        )

    if not isinstance(
        data,
        dict,
    ):

        raise RuntimeGraphError(
            f"Invalid YAML root: {path}"
        )

    return data


def digest(
    value: Any,
) -> str:

    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


def write_json(
    path: Path,
    payload: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        path,
    )


class RuntimeGraph:

    def __init__(
        self,
    ) -> None:

        data = load_yaml(
            REGISTRY
        )

        runtime = data.get(
            "runtime"
        )

        if not isinstance(
            runtime,
            dict,
        ):

            raise RuntimeGraphError(
                "runtime must be an object"
            )

        self.registry = data
        self.runtime = runtime

        self.execution_order = [
            str(
                value
            ).strip()
            for value
            in runtime.get(
                "execution_order",
                [],
            )
            if str(
                value
            ).strip()
        ]

        subsystems = runtime.get(
            "subsystems",
            {},
        )

        if not isinstance(
            subsystems,
            dict,
        ):

            raise RuntimeGraphError(
                "subsystems must be an object"
            )

        self.subsystems = subsystems

    def resolve_controller(
        self,
        subsystem: str,
    ) -> Path:

        record = self.subsystems.get(
            subsystem
        )

        if not isinstance(
            record,
            dict,
        ):

            raise KeyError(
                subsystem
            )

        controller = str(
            record.get(
                "controller",
                "",
            )
        ).strip()

        if not controller:

            raise RuntimeGraphError(
                f"Controller missing: {subsystem}"
            )

        return (
            LEXICON_ROOT
            / controller
        )

    def nodes(
        self,
    ) -> list[dict[str, Any]]:

        nodes = [
            {
                "id": self.runtime[
                    "id"
                ],
                "type": "runtime",
                "canonical": self.runtime.get(
                    "canonical"
                ),
                "status": self.runtime.get(
                    "status"
                ),
                "version": self.runtime.get(
                    "version"
                ),
                "authority": self.runtime.get(
                    "authority"
                ),
            }
        ]

        for position, subsystem in enumerate(
            self.execution_order
        ):

            record = self.subsystems.get(
                subsystem,
                {},
            )

            controller = self.resolve_controller(
                subsystem
            )

            nodes.append(
                {
                    "id": record.get(
                        "id",
                        (
                            "runtime:subsystem:"
                            f"{subsystem}"
                        ),
                    ),
                    "type": "runtime_subsystem",
                    "canonical": subsystem,
                    "position": position,
                    "required": bool(
                        record.get(
                            "required",
                            True,
                        )
                    ),
                    "controller": str(
                        controller
                    ),
                    "controller_exists": (
                        controller.is_file()
                    ),
                    "controller_executable": (
                        controller.is_file()
                        and os.access(
                            controller,
                            os.X_OK,
                        )
                    ),
                    "actions": record.get(
                        "actions",
                        {},
                    ),
                }
            )

        return nodes

    def edges(
        self,
    ) -> list[dict[str, Any]]:

        edges = []

        runtime_id = str(
            self.runtime[
                "id"
            ]
        )

        previous_id: str | None = None

        for position, subsystem in enumerate(
            self.execution_order
        ):

            record = self.subsystems.get(
                subsystem,
                {},
            )

            subsystem_id = str(
                record.get(
                    "id",
                    (
                        "runtime:subsystem:"
                        f"{subsystem}"
                    ),
                )
            )

            edges.append(
                {
                    "id": (
                        "runtime:edge:contains:"
                        f"{subsystem}"
                    ),
                    "from": runtime_id,
                    "to": subsystem_id,
                    "relation": "contains",
                    "position": position,
                }
            )

            if previous_id is not None:

                edges.append(
                    {
                        "id": (
                            "runtime:edge:precedes:"
                            f"{self.execution_order[position - 1]}"
                            f":{subsystem}"
                        ),
                        "from": previous_id,
                        "to": subsystem_id,
                        "relation": "precedes",
                    }
                )

            previous_id = subsystem_id

        for dependency in sorted(
            set(
                str(
                    value
                ).strip()
                for value
                in self.runtime.get(
                    "dependencies",
                    [],
                )
                if str(
                    value
                ).strip()
            )
        ):

            edges.append(
                {
                    "id": (
                        "runtime:edge:depends_on:"
                        + dependency.replace(
                            ":",
                            "_",
                        )
                    ),
                    "from": runtime_id,
                    "to": dependency,
                    "relation": "depends_on",
                }
            )

        return edges

    def dependencies(
        self,
    ) -> dict[str, Any]:

        records = []

        for subsystem in self.execution_order:

            controller = self.resolve_controller(
                subsystem
            )

            record = self.subsystems[
                subsystem
            ]

            records.append(
                {
                    "subsystem": subsystem,
                    "id": record.get(
                        "id"
                    ),
                    "controller": str(
                        controller
                    ),
                    "exists": controller.is_file(),
                    "executable": (
                        controller.is_file()
                        and os.access(
                            controller,
                            os.X_OK,
                        )
                    ),
                    "required": bool(
                        record.get(
                            "required",
                            True,
                        )
                    ),
                }
            )

        unresolved = [
            record
            for record in records
            if record[
                "required"
            ]
            and (
                not record[
                    "exists"
                ]
                or not record[
                    "executable"
                ]
            )
        ]

        return {
            "resolved": not unresolved,
            "records": records,
            "unresolved": unresolved,
        }

    def graph(
        self,
    ) -> dict[str, Any]:

        nodes = self.nodes()
        edges = self.edges()

        payload = {
            "runtime": self.runtime[
                "id"
            ],
            "nodes": nodes,
            "edges": edges,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def provenance(
        self,
    ) -> dict[str, Any]:

        payload = {
            "runtime": self.runtime[
                "id"
            ],
            "provenance": self.runtime.get(
                "provenance",
                {},
            ),
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def lineage(
        self,
    ) -> dict[str, Any]:

        payload = {
            "runtime": self.runtime[
                "id"
            ],
            "lineage": self.runtime.get(
                "lineage",
                {},
            ),
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def snapshot(
        self,
    ) -> dict[str, Any]:

        dependencies = self.dependencies()
        graph = self.graph()
        provenance = self.provenance()
        lineage = self.lineage()

        payload = {
            "runtime": self.runtime[
                "id"
            ],
            "ready": dependencies[
                "resolved"
            ],
            "execution_order": (
                self.execution_order
            ),
            "subsystem_count": len(
                self.execution_order
            ),
            "graph_digest": graph[
                "digest"
            ],
            "provenance_digest": (
                provenance[
                    "digest"
                ]
            ),
            "lineage_digest": lineage[
                "digest"
            ],
            "dependencies": dependencies,
        }

        payload[
            "digest"
        ] = digest(
            payload
        )

        return payload

    def materialize(
        self,
        output: Path,
    ) -> dict[str, Any]:

        outputs = {
            "runtime_graph.json": (
                self.graph()
            ),
            "runtime_dependencies.json": (
                self.dependencies()
            ),
            "runtime_provenance.json": (
                self.provenance()
            ),
            "runtime_lineage.json": (
                self.lineage()
            ),
            "runtime_snapshot.json": (
                self.snapshot()
            ),
        }

        for filename, payload in (
            outputs.items()
        ):

            write_json(
                output
                / filename,
                payload,
            )

        manifest = {
            "runtime": self.runtime[
                "id"
            ],
            "output": str(
                output.resolve()
            ),
            "files": sorted(
                outputs
            ),
            "snapshot": outputs[
                "runtime_snapshot.json"
            ],
        }

        manifest[
            "digest"
        ] = digest(
            manifest
        )

        write_json(
            output
            / "runtime_graph_manifest.json",
            manifest,
        )

        return manifest


def main() -> int:

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "graph"
    )

    subparsers.add_parser(
        "dependencies"
    )

    subparsers.add_parser(
        "provenance"
    )

    subparsers.add_parser(
        "lineage"
    )

    subparsers.add_parser(
        "snapshot"
    )

    materialize_parser = subparsers.add_parser(
        "materialize"
    )

    materialize_parser.add_argument(
        "--output",
        default=str(
            DEFAULT_OUTPUT
        ),
    )

    args = parser.parse_args()

    runtime = RuntimeGraph()

    if args.command == "graph":

        result = runtime.graph()

    elif args.command == "dependencies":

        result = runtime.dependencies()

    elif args.command == "provenance":

        result = runtime.provenance()

    elif args.command == "lineage":

        result = runtime.lineage()

    elif args.command == "snapshot":

        result = runtime.snapshot()

    elif args.command == "materialize":

        result = runtime.materialize(
            Path(
                args.output
            )
        )

    else:

        raise RuntimeGraphError(
            args.command
        )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    if args.command == "dependencies":

        return (
            0
            if result[
                "resolved"
            ]
            else 1
        )

    if args.command == "snapshot":

        return (
            0
            if result[
                "ready"
            ]
            else 1
        )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
