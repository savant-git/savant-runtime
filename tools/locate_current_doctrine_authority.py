#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Iterator


ROOT = Path("/root/savant-runtime")

OUTPUT_ROOT = (
    ROOT
    / "audit"
    / "authority-input-resolution"
)

OUTPUT_JSON = (
    OUTPUT_ROOT
    / "current_doctrine_authority_candidates.json"
)

MAX_FILE_BYTES = 32 * 1024 * 1024

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
}

EXCLUDED_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}

TARGETS = {
    "master_doctrine": (
        "master_doctrine",
        "master-doctrine",
        "master doctrine",
    ),
    "construction_constitution": (
        "construction_constitution",
        "construction-constitution",
        "construction constitution",
        "chat_rules",
        "chat-rules",
        "chat rules",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def iter_files() -> Iterator[Path]:
    for directory, directories, files in os.walk(
        ROOT
    ):
        directories[:] = [
            name
            for name in directories
            if name not in EXCLUDED_DIR_NAMES
        ]

        base = Path(directory)

        for name in files:
            path = base / name

            try:
                stat = path.stat()
            except OSError:
                continue

            if not path.is_file():
                continue

            if stat.st_size > MAX_FILE_BYTES:
                continue

            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue

            yield path


def read_prefix(
    path: Path,
    limit: int = 65536,
) -> str:
    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:
            return handle.read(limit)

    except OSError:
        return ""


def match_score(
    path: Path,
    text: str,
    terms: tuple[str, ...],
) -> tuple[int, list[str]]:
    filename = path.name.lower()
    relative = str(
        path.relative_to(ROOT)
    ).lower()

    text_lower = text.lower()

    score = 0
    reasons: list[str] = []

    for term in terms:
        normalized = term.lower()

        if normalized in filename:
            score += 20
            reasons.append(
                f"filename:{term}"
            )

        elif normalized in relative:
            score += 10
            reasons.append(
                f"path:{term}"
            )

        if normalized in text_lower:
            score += 4
            reasons.append(
                f"content:{term}"
            )

    if "accepted" in text_lower:
        score += 2
        reasons.append(
            "content:accepted"
        )

    if "authority" in text_lower:
        score += 2
        reasons.append(
            "content:authority"
        )

    if "canonical" in text_lower:
        score += 2
        reasons.append(
            "content:canonical"
        )

    if "proposed" in text_lower:
        score -= 2
        reasons.append(
            "content:proposed"
        )

    if "historical" in text_lower:
        score -= 1
        reasons.append(
            "content:historical"
        )

    return score, reasons


def candidate_record(
    path: Path,
    score: int,
    reasons: list[str],
) -> dict[str, object]:
    stat = path.stat()

    return {
        "path": str(path),
        "relative_path": str(
            path.relative_to(ROOT)
        ),
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
        "score": score,
        "reasons": reasons,
    }


def main() -> int:
    if not ROOT.is_dir():
        print(
            f"runtime root does not exist: {ROOT}",
            file=sys.stderr,
        )
        return 1

    results: dict[
        str,
        list[dict[str, object]],
    ] = {
        name: []
        for name in TARGETS
    }

    files_examined = 0

    for path in iter_files():
        files_examined += 1

        text = read_prefix(path)

        for target, terms in TARGETS.items():
            score, reasons = match_score(
                path,
                text,
                terms,
            )

            if score <= 0:
                continue

            results[target].append(
                candidate_record(
                    path,
                    score,
                    reasons,
                )
            )

    for candidates in results.values():
        candidates.sort(
            key=lambda item: (
                -int(item["score"]),
                str(item["path"]),
            )
        )

    compact_results = {
        target: candidates[:20]
        for target, candidates in results.items()
    }

    summary = {
        "runtime_root": str(ROOT),
        "files_examined": files_examined,
        "authority_effect": "none",
        "authority_note": (
            "filesystem discovery establishes "
            "candidate location only; presence, "
            "filename, content, or modification "
            "time does not establish authority"
        ),
        "targets": compact_results,
        "candidate_counts": {
            target: len(candidates)
            for target, candidates in results.items()
        },
    }

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_JSON.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
