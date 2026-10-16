#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from piece_engine import execute_pieces


BASE = Path(__file__).resolve().parents[1]
REGISTRY = BASE / "registry"


def load_json(
    path: Path,
) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def digest(
    value: Any,
) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


def valid_piece_count(
    count: int,
) -> bool:
    return (
        count == 3
        or (
            count > 0
            and count % 9 == 0
        )
    )


def piece_lookup() -> dict[
    str,
    dict[str, Any],
]:
    document = load_json(
        REGISTRY
        / "pieces.json"
    )

    pieces = {
        item["id"]: item
        for item
        in document["pieces"]
    }

    if len(pieces) != 81:
        raise RuntimeError(
            "Coalesce requires exactly eighty-one registered pieces"
        )

    return pieces


def recipe_lookup() -> dict[
    str,
    dict[str, Any],
]:
    document = load_json(
        REGISTRY
        / "recipes.json"
    )

    lookup: dict[
        str,
        dict[str, Any],
    ] = {}

    for recipe in document[
        "recipes"
    ]:
        canonical_id = str(
            recipe["id"]
        )

        short_id = str(
            recipe["recipe_id"]
        )

        lookup[
            canonical_id
        ] = recipe

        lookup[
            short_id
        ] = recipe

    return lookup


def resolve_recipe(
    identity: str,
) -> dict[str, Any]:
    recipes = recipe_lookup()

    if identity not in recipes:
        raise KeyError(
            f"unknown Coalesce recipe: {identity}"
        )

    return copy.deepcopy(
        recipes[
            identity
        ]
    )


def compile_recipe(
    identity: str,
) -> dict[str, Any]:
    recipe = resolve_recipe(
        identity
    )

    pieces = piece_lookup()

    selected = [
        copy.deepcopy(
            pieces[
                piece_id
            ]
        )
        for piece_id
        in recipe[
            "piece_ids"
        ]
    ]

    selected.sort(
        key=lambda item: (
            item[
                "service_ordinal"
            ],
            item[
                "piece_ordinal"
            ],
        )
    )

    count = len(
        selected
    )

    if not valid_piece_count(
        count
    ):
        raise RuntimeError(
            (
                "Coalesce composition "
                "cardinality violation: "
                f"{count}"
            )
        )

    compiled = {
        "id": (
            "wavre:coalesce:"
            f"{recipe['recipe_id']}"
        ),
        "kind": (
            "application_wavre"
        ),
        "owner": (
            "prodigal:modus:coalesce"
        ),
        "source_recipe": (
            recipe["id"]
        ),
        "recipe": recipe,
        "piece_count": count,
        "piece_ids": [
            item["id"]
            for item in selected
        ],
        "pieces": selected,
        "composition": (
            "reference"
        ),
        "authority_effect": (
            "none"
        ),
    }

    compiled[
        "composition_digest"
    ] = digest(
        compiled
    )

    return compiled


def normalize_context(
    context: Any,
) -> dict[str, Any]:
    if context is None:
        context = {}

    if not isinstance(
        context,
        dict,
    ):
        raise TypeError(
            "Coalesce execution context must be an object"
        )

    result = copy.deepcopy(
        context
    )

    result.setdefault(
        "records",
        [],
    )

    result.setdefault(
        "state",
        {},
    )

    result.setdefault(
        "parameters",
        {},
    )

    result.setdefault(
        "artifacts",
        {},
    )

    result.setdefault(
        "trace",
        [],
    )

    if not isinstance(
        result[
            "records"
        ],
        list,
    ):
        raise TypeError(
            "context.records must be a list"
        )

    if not isinstance(
        result[
            "state"
        ],
        dict,
    ):
        raise TypeError(
            "context.state must be an object"
        )

    if not isinstance(
        result[
            "parameters"
        ],
        dict,
    ):
        raise TypeError(
            "context.parameters must be an object"
        )

    if not isinstance(
        result[
            "artifacts"
        ],
        dict,
    ):
        raise TypeError(
            "context.artifacts must be an object"
        )

    return result


def execute_recipe(
    identity: str,
    context: dict[
        str,
        Any,
    ],
) -> dict[str, Any]:
    compiled = compile_recipe(
        identity
    )

    working = normalize_context(
        context
    )

    working[
        "coalesce"
    ] = {
        "recipe": (
            compiled[
                "source_recipe"
            ]
        ),
        "wavre": (
            compiled[
                "id"
            ]
        ),
        "piece_count": (
            compiled[
                "piece_count"
            ]
        ),
        "composition_digest": (
            compiled[
                "composition_digest"
            ]
        ),
        "authority_effect": (
            "none"
        ),
    }

    result = execute_pieces(
        compiled[
            "piece_ids"
        ],
        working,
    )

    result.setdefault(
        "artifacts",
        {},
    )

    result[
        "artifacts"
    ][
        "coalesce_execution"
    ] = {
        "recipe": (
            compiled[
                "source_recipe"
            ]
        ),
        "wavre": (
            compiled[
                "id"
            ]
        ),
        "piece_count": (
            compiled[
                "piece_count"
            ]
        ),
        "composition_digest": (
            compiled[
                "composition_digest"
            ]
        ),
        "executed_piece_count": len(
            result.get(
                "trace",
                [],
            )
        ),
        "authority_effect": (
            "none"
        ),
    }

    return result


def list_recipes() -> dict[
    str,
    Any,
]:
    document = load_json(
        REGISTRY
        / "recipes.json"
    )

    recipes = []

    for recipe in document[
        "recipes"
    ]:
        recipes.append(
            {
                "id": (
                    recipe[
                        "id"
                    ]
                ),
                "recipe_id": (
                    recipe[
                        "recipe_id"
                    ]
                ),
                "title": (
                    recipe[
                        "title"
                    ]
                ),
                "piece_count": (
                    recipe[
                        "piece_count"
                    ]
                ),
                "services": (
                    recipe[
                        "services"
                    ]
                ),
            }
        )

    return {
        "id": (
            "sear:coalesce:"
            "recipes"
        ),
        "owner": (
            "prodigal:modus:coalesce"
        ),
        "recipe_count": len(
            recipes
        ),
        "recipes": recipes,
    }


def load_context_argument(
    raw_context: str | None,
    context_file: str | None,
) -> dict[str, Any]:
    if (
        raw_context
        and context_file
    ):
        raise ValueError(
            (
                "use either --context "
                "or --context-file, not both"
            )
        )

    if context_file:
        path = Path(
            context_file
        )

        return normalize_context(
            json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        )

    if raw_context:
        return normalize_context(
            json.loads(
                raw_context
            )
        )

    return normalize_context(
        {}
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="coalesce"
    )

    parser.add_argument(
        "operation",
        choices=[
            "list",
            "compile",
            "execute",
        ],
    )

    parser.add_argument(
        "recipe",
        nargs="?",
    )

    parser.add_argument(
        "--context",
    )

    parser.add_argument(
        "--context-file",
    )

    args = parser.parse_args()

    if args.operation == "list":
        print(
            json.dumps(
                list_recipes(),
                indent=2,
                sort_keys=True,
            )
        )

        return 0

    if not args.recipe:
        parser.error(
            (
                f"{args.operation} "
                "requires a Coalesce recipe"
            )
        )

    if args.operation == "compile":
        result = compile_recipe(
            args.recipe
        )

    else:
        context = (
            load_context_argument(
                args.context,
                args.context_file,
            )
        )

        result = execute_recipe(
            args.recipe,
            context,
        )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
