#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


schema = "savant.niche.atlas-static-projection.v1"
authority_effect = "none"
owner = "exile:niche"
projection_only = True
mutation_authority = False

app_root = Path(
    "/root/savant-runtime/"
    "ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/atlas"
)

assets_root = app_root / "assets"
target = assets_root / "atlas.json"

if str(app_root) not in sys.path:
    sys.path.insert(
        0,
        str(app_root),
    )

from atlas_projection import atlas_projection


def canonical_bytes(
    value: object,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def atomic_write(
    path: Path,
    substance: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as handle:
            handle.write(
                substance
            )

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    projection = atlas_projection()

    if projection.get(
        "projection_only"
    ) is not True:
        raise RuntimeError(
            "Atlas projection attempted "
            "to acquire non-projection authority"
        )

    if projection.get(
        "mutation_authority"
    ) is not False:
        raise RuntimeError(
            "Atlas projection attempted "
            "to acquire mutation authority"
        )

    substance = canonical_bytes(
        projection
    )

    atomic_write(
        target,
        substance,
    )

    print(
        json.dumps(
            {
                "schema": schema,
                "authority_effect":
                    authority_effect,
                "owner":
                    owner,
                "status":
                    "passed",
                "projection_only":
                    projection_only,
                "mutation_authority":
                    mutation_authority,
                "target":
                    str(target),
                "bytes":
                    len(substance),
                "nodes":
                    len(
                        projection.get(
                            "nodes",
                            [],
                        )
                    ),
                "edges":
                    len(
                        projection.get(
                            "edges",
                            [],
                        )
                    ),
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
