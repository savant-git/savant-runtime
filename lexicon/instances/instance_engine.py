#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent

INSTANCE_REGISTRY = ROOT / "instance_registry.yaml"
SEGUE_REGISTRY = ROOT / "segue_registry.yaml"


class InstanceEngine:

    def __init__(self):

        self.instances = {}
        self.segues = {}

        self.kindred_index = defaultdict(set)
        self.ontology_index = defaultdict(set)
        self.source_index = defaultdict(set)

        self.dependency_graph = defaultdict(set)
        self.dependent_graph = defaultdict(set)

        self.outgoing = defaultdict(set)
        self.incoming = defaultdict(set)

        self.load()

    def load(self):

        with INSTANCE_REGISTRY.open(
            "r",
            encoding="utf-8",
        ) as f:

            registry = yaml.safe_load(f)

        for instance in registry["instances"]:

            iid = instance["id"]

            self.instances[iid] = instance

            for kindred in instance.get(
                "kindreds",
                [],
            ):

                self.kindred_index[
                    kindred
                ].add(iid)

            for ontology in instance.get(
                "ontology",
                [],
            ):

                self.ontology_index[
                    ontology
                ].add(iid)

            source = instance.get(
                "source",
                {},
            ).get(
                "reference"
            )

            if source:

                self.source_index[
                    source
                ].add(iid)

            for dependency in instance.get(
                "dependencies",
                [],
            ):

                self.dependency_graph[
                    iid
                ].add(
                    dependency
                )

                self.dependent_graph[
                    dependency
                ].add(
                    iid
                )

        with SEGUE_REGISTRY.open(
            "r",
            encoding="utf-8",
        ) as f:

            registry = yaml.safe_load(f)

        for segue in registry["segues"]:

            sid = segue["id"]

            self.segues[sid] = segue

            src = segue["from"]
            dst = segue["to"]

            self.outgoing[src].add(sid)
            self.incoming[dst].add(sid)

            for dependency in segue.get(
                "dependencies",
                [],
            ):

                self.dependency_graph[
                    sid
                ].add(
                    dependency
                )

                self.dependent_graph[
                    dependency
                ].add(
                    sid
                )

    def resolve(
        self,
        reference,
    ):

        if reference in self.instances:

            return self.instances[
                reference
            ]

        if reference in self.segues:

            return self.segues[
                reference
            ]

        raise KeyError(reference)

    def search(
        self,
        query,
    ):

        q = query.lower()

        results = []

        for collection in (
            self.instances,
            self.segues,
        ):

            for rid, record in collection.items():

                blob = json.dumps(
                    record
                ).lower()

                if q in blob:

                    results.append(
                        rid
                    )

        return sorted(results)

    def graph(self):

        nodes = []

        edges = []

        for iid, record in self.instances.items():

            nodes.append(
                {
                    "id": iid,
                    "type": "instance",
                    "canonical": record[
                        "canonical"
                    ],
                }
            )

            for dep in record.get(
                "dependencies",
                [],
            ):

                edges.append(
                    {
                        "type": "depends_on",
                        "source": iid,
                        "target": dep,
                    }
                )

        for sid, record in self.segues.items():

            nodes.append(
                {
                    "id": sid,
                    "type": "segue",
                    "canonical": record[
                        "canonical"
                    ],
                }
            )

            edges.append(
                {
                    "type": record[
                        "relation"
                    ],
                    "source": record[
                        "from"
                    ],
                    "target": record[
                        "to"
                    ],
                    "segue": sid,
                }
            )

        return {

            "nodes": nodes,

            "edges": edges,

        }

    def snapshot(self):

        digest = hashlib.sha256(

            json.dumps(
                self.graph(),
                sort_keys=True,
            ).encode()

        ).hexdigest()

        return {

            "instances":
                len(
                    self.instances
                ),

            "segues":
                len(
                    self.segues
                ),

            "digest":
                digest,

        }

    def project(
        self,
        output,
    ):

        output.mkdir(
            parents=True,
            exist_ok=True,
        )

        files = {

            "graph.json":
                self.graph(),

            "snapshot.json":
                self.snapshot(),

            "kindred_index.json":
                {
                    k: sorted(v)
                    for k, v
                    in self.kindred_index.items()
                },

            "ontology_index.json":
                {
                    k: sorted(v)
                    for k, v
                    in self.ontology_index.items()
                },

            "source_index.json":
                {
                    k: sorted(v)
                    for k, v
                    in self.source_index.items()
                },

        }

        for filename, payload in files.items():

            tmp = output / (
                "." + filename
            )

            tmp.write_text(

                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                ),

                encoding="utf-8",

            )

            os.replace(
                tmp,
                output / filename,
            )


def main():

    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser(
        "graph"
    )

    sub.add_parser(
        "snapshot"
    )

    search = sub.add_parser(
        "search"
    )

    search.add_argument(
        "query"
    )

    resolve = sub.add_parser(
        "resolve"
    )

    resolve.add_argument(
        "reference"
    )

    project = sub.add_parser(
        "project"
    )

    project.add_argument(
        "--output",
        default=str(
            ROOT / "runtime"
        ),
    )

    args = parser.parse_args()

    engine = InstanceEngine()

    if args.command == "graph":

        print(
            json.dumps(
                engine.graph(),
                indent=2,
            )
        )

    elif args.command == "snapshot":

        print(
            json.dumps(
                engine.snapshot(),
                indent=2,
            )
        )

    elif args.command == "search":

        print(
            json.dumps(
                engine.search(
                    args.query
                ),
                indent=2,
            )
        )

    elif args.command == "resolve":

        print(
            json.dumps(
                engine.resolve(
                    args.reference
                ),
                indent=2,
            )
        )

    elif args.command == "project":

        engine.project(
            Path(
                args.output
            )
        )


if __name__ == "__main__":

    main()
