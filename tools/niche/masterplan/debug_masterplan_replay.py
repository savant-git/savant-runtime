#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("/root/savant-runtime")

AUTHORITATIVE = (
    ROOT
    / "authority"
    / "task-graph"
    / "masterplan.json"
)

REPLAY = (
    ROOT
    / "runtime"
    / "masterplan"
    / "replay"
    / "latest.json"
)


def load(path: Path):
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def key(segue):
    return (
        segue["type"],
        segue["source"],
        segue["target"],
        segue["id"],
    )


def main():
    authority = load(
        AUTHORITATIVE
    )

    replay = load(
        REPLAY
    )

    authoritative = {
        key(x)
        for x in authority["segues"]
    }

    replayed = {
        key(x)
        for x in replay["segues"]
    }

    print(
        json.dumps(
            {
                "authoritative_count": len(authoritative),
                "replayed_count": len(replayed),
                "missing_from_replay": sorted(
                    authoritative - replayed
                ),
                "extra_in_replay": sorted(
                    replayed - authoritative
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
