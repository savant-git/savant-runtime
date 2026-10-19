
#!/usr/bin/env python3
"""Read-only, bounded source-evidence projection from a Savant sdump."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = "savant.urchin.evidence_projection.v1"
BEGIN = b"=== file ==="
CONTENT = b"=== content ==="
END = b"=== /file ==="
MAX_LINE = 1048576


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def records(snapshot: Path):
    with gzip.open(snapshot, "rb") as stream:
        state = 0
        metadata = None
        content = hashlib.sha256()
        length = 0

        for raw in stream:
            marker = raw.rstrip(b"\r\n")

            if state == 0:
                if marker == BEGIN:
                    state = 1

            elif state == 1:
                if len(marker) > MAX_LINE:
                    raise ValueError("oversized file metadata")

                try:
                    metadata = json.loads(marker)
                except (ValueError, UnicodeError) as exc:
                    raise ValueError("invalid sdump metadata") from exc

                if not isinstance(metadata, dict) or not isinstance(
                    metadata.get("path"), str
                ):
                    raise ValueError("invalid sdump path metadata")

                state = 2

            elif state == 2:
                if marker != CONTENT:
                    raise ValueError("missing content marker")

                content = hashlib.sha256()
                length = 0
                state = 3

            elif marker == END:
                yield metadata, content.hexdigest(), length
                state = 0

            else:
                content.update(raw)
                length += len(raw)

        if state != 0:
            raise ValueError("truncated sdump file record")


def extract(snapshot: Path, doctrine: Path, limit: int):
    text = doctrine.read_text(encoding="utf-8").casefold()

    candidates = []
    seen = set()

    counts = {
        "files_seen": 0,
        "duplicates": 0,
        "documented_literal": 0,
        "candidates": 0,
    }

    for meta, sha256, captured_bytes in records(snapshot):
        path = meta["path"]
        counts["files_seen"] += 1

        if path in seen:
            counts["duplicates"] += 1
            continue

        seen.add(path)
        name = Path(path).name

        if path.casefold() in text or (
            len(name) >= 12 and name.casefold() in text
        ):
            counts["documented_literal"] += 1
            continue

        counts["candidates"] += 1

        if len(candidates) < limit:
            candidates.append({
                "candidate_id": (
                    "candidate:"
                    + digest(path.encode("utf-8"))[:24]
                ),
                "source_path": path,
                "source_sha256": sha256,
                "captured_bytes": captured_bytes,
                "claimed_size": meta.get("size"),
                "authority": "unresolved",
                "urchin": "unconfirmed",
                "frag": "unconfirmed",
                "description": None,
            })

    return {
        "schema": SCHEMA,
        "authority_effect": "none",
        "snapshot": snapshot.name,
        "doctrine": doctrine.name,
        "counts": counts,
        "candidate_sample_limit": limit,
        "candidates": candidates,
        "lexicon_proposals": [{
            "term": "urchin",
            "definition": (
                "implementation found in source but not yet "
                "reconciled with accepted doctrine"
            ),
            "status": "user_directive_pending_canonical_admission",
        }],
        "cautions": [
            "literal documentation matching is not semantic reconciliation",
            "source files are not equivalent to frags or urchins",
            "sdump record framing may not preserve exact source bytes",
            "no vagary, spasm, or iota instances are inferred",
            "no authoritative file is modified",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--snapshot",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--doctrine",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
    )

    args = parser.parse_args()

    if not 0 <= args.limit <= 10000:
        parser.error("--limit must be between 0 and 10000")

    try:
        result = extract(
            args.snapshot,
            args.doctrine,
            args.limit,
        )
    except (OSError, ValueError, EOFError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(
        result,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
