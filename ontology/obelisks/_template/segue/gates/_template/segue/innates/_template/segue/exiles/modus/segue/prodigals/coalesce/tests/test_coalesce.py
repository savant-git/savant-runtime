#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]


def main() -> int:
    pieces = json.loads(
        (
            BASE
            / "registry"
            / "pieces.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    recipes = json.loads(
        (
            BASE
            / "registry"
            / "recipes.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    moods = json.loads(
        (
            BASE
            / "moods"
            / "bindings.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert pieces["service_count"] == 9
    assert pieces["pieces_per_service"] == 9
    assert pieces["piece_count"] == 81
    assert len(pieces["pieces"]) == 81

    assert recipes["recipe_count"] == 9
    assert len(recipes["recipes"]) == 9

    assert moods["binding_count"] == 27

    for recipe in recipes["recipes"]:
        count = recipe["piece_count"]

        assert (
            count == 3
            or count % 9 == 0
        )

    result = subprocess.run(
        [
            "python3",
            str(
                BASE
                / "runtime"
                / "coalesce.py"
            ),
            "compile",
            "chronology-explorer",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    compiled = json.loads(
        result.stdout
    )

    assert compiled["piece_count"] % 9 == 0
    assert compiled["composition_digest"]
    assert compiled["owner"] == "prodigal:modus:coalesce"

    print("COALESCE: valid")

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
