from __future__ import annotations

from pathlib import Path

from ENTITY_DISCOVERY import discover_entities


def print_tree():

    entities = sorted(
        discover_entities(),
        key=lambda e: Path(e.path)
    )

    for entity in entities:
        depth = len(Path(entity.path).parts)

        print(
            "    " * depth +
            f"{entity.type}: {entity.id}"
        )


if __name__ == "__main__":
    print_tree()
