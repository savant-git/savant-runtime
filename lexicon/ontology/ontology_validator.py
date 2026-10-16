#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent

REGISTRY = ROOT / "ontology_registry.yaml"


def load():

    with REGISTRY.open(
        "r",
        encoding="utf-8",
    ) as f:

        return yaml.safe_load(f)


def validate(data):

    ids = set()

    errors = []

    for cls in data["classes"]:

        cid = cls["id"]

        if cid in ids:

            errors.append(
                f"Duplicate ontology id: {cid}"
            )

        ids.add(cid)

    for cls in data["classes"]:

        for parent in cls.get(
            "parents",
            [],
        ):

            if parent not in ids:

                errors.append(
                    f"{cls['id']} "
                    f"references "
                    f"unknown parent "
                    f"{parent}"
                )

    return errors


def main():

    data = load()

    errors = validate(data)

    print(
        json.dumps(
            {
                "valid": not errors,
                "errors": errors,
            },
            indent=2,
        )
    )

    raise SystemExit(
        1 if errors else 0
    )


if __name__ == "__main__":
    main()
