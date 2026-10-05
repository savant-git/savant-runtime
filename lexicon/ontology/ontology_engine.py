#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent

REGISTRY = ROOT / "ontology_registry.yaml"


class Ontology:

    def __init__(self):

        with REGISTRY.open(
            "r",
            encoding="utf-8",
        ) as f:

            self.data = yaml.safe_load(f)

        self.classes = {}

        for cls in self.data["classes"]:

            self.classes[
                cls["id"]
            ] = cls

    def get(
        self,
        cid,
    ):

        return self.classes[cid]

    def parents(
        self,
        cid,
    ):

        return self.classes[
            cid
        ].get(
            "parents",
            [],
        )

    def children(
        self,
        cid,
    ):

        return self.classes[
            cid
        ].get(
            "children",
            [],
        )

    def dump(self):

        print(
            json.dumps(
                self.data,
                indent=2,
            )
        )


if __name__ == "__main__":

    Ontology().dump()
