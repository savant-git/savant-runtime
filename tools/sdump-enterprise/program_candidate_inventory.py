from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
import sys
from typing import Any


RUNTIME_ROOT = Path(
    "/root/savant-runtime"
)

SDUMP_ROOT = (
    RUNTIME_ROOT
    / "tools"
    / "sdump-enterprise"
)

PROFILE_ID = "code"

TOP_FILE_LIMIT = 200
TOP_DIRECTORY_LIMIT = 100
TOP_EXTENSION_LIMIT = 100


if str(SDUMP_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(SDUMP_ROOT),
    )


from sdump_enterprise import profiles
from sdump_enterprise.scan import discover


def load_code_profile() -> Any:
    loader = getattr(
        profiles,
        "load_profile",
        None,
    )

    if not callable(loader):
        raise RuntimeError(
            "sdump_enterprise.profiles.load_profile "
            "is unavailable"
        )

    return loader(
        PROFILE_ID
    )


def candidate_path(
    candidate: Any,
) -> Path:
    for field in (
        "path",
        "source_path",
        "absolute_path",
        "file_path",
    ):
        value = getattr(
            candidate,
            field,
            None,
        )

        if value is None:
            continue

        path = Path(value)

        if path.is_absolute():
            return path

        return (
            RUNTIME_ROOT
            / path
        )

    raise RuntimeError(
        "candidate does not expose "
        "a recognized path field"
    )


def candidate_size(
    candidate: Any,
    path: Path,
) -> int:
    for field in (
        "size",
        "size_bytes",
        "source_bytes",
        "byte_size",
        "st_size",
    ):
        value = getattr(
            candidate,
            field,
            None,
        )

        if (
            isinstance(value, int)
            and value >= 0
        ):
            return value

    return path.stat().st_size


def relative_path(
    path: Path,
) -> str:
    try:
        return (
            path.relative_to(
                RUNTIME_ROOT
            )
            .as_posix()
        )

    except ValueError:
        return path.as_posix()


def mib(
    value: int,
) -> float:
    return (
        value
        / 1048576
    )


def candidate_metadata(
    candidate: Any,
) -> dict[str, Any]:
    if is_dataclass(candidate):
        try:
            payload = asdict(
                candidate
            )

            if isinstance(
                payload,
                dict,
            ):
                return payload

        except Exception:
            pass

    try:
        payload = vars(
            candidate
        )

        if isinstance(
            payload,
            dict,
        ):
            return dict(
                payload
            )

    except TypeError:
        pass

    return {}


def normalized_suffix(
    path: Path,
) -> str:
    suffix = (
        path.suffix.casefold()
    )

    if suffix:
        return suffix

    return "<extensionless>"


def directory_family(
    relative: str,
    depth: int,
) -> str:
    parts = Path(
        relative
    ).parts

    if not parts:
        return "."

    return "/".join(
        parts[
            : min(
                depth,
                len(parts),
            )
        ]
    )


def emit_group(
    title: str,
    rows: list[
        tuple[int, int, str]
    ],
    limit: int,
) -> None:
    print()
    print(title)
    print()

    for (
        size,
        count,
        name,
    ) in rows[:limit]:
        print(
            f"{mib(size):12.2f} MiB  "
            f"{count:8d} files  "
            f"{name}"
        )


def main() -> int:
    profile = load_code_profile()

    (
        candidates,
        skipped,
        failures,
        symlinks,
        stats,
    ) = discover(
        targets=[
            RUNTIME_ROOT
        ],
        profile=profile,
        absolute_excluded_roots=(),
        include_hidden=False,
        include_secrets=False,
        extra_patterns=(),
        respect_gitignore=False,
    )

    files: list[
        tuple[
            int,
            str,
            str,
        ]
    ] = []

    top_level: dict[
        str,
        list[int],
    ] = defaultdict(
        lambda: [0, 0]
    )

    depth_two: dict[
        str,
        list[int],
    ] = defaultdict(
        lambda: [0, 0]
    )

    depth_three: dict[
        str,
        list[int],
    ] = defaultdict(
        lambda: [0, 0]
    )

    extensions: dict[
        str,
        list[int],
    ] = defaultdict(
        lambda: [0, 0]
    )

    total_bytes = 0

    inaccessible = 0

    for candidate in candidates:
        try:
            path = candidate_path(
                candidate
            )

            size = candidate_size(
                candidate,
                path,
            )

            relative = relative_path(
                path
            )

            suffix = normalized_suffix(
                path
            )

        except (
            OSError,
            RuntimeError,
            ValueError,
        ):
            inaccessible += 1
            continue

        total_bytes += size

        files.append(
            (
                size,
                relative,
                suffix,
            )
        )

        top = directory_family(
            relative,
            1,
        )

        second = directory_family(
            relative,
            2,
        )

        third = directory_family(
            relative,
            3,
        )

        top_level[top][0] += size
        top_level[top][1] += 1

        depth_two[second][0] += size
        depth_two[second][1] += 1

        depth_three[third][0] += size
        depth_three[third][1] += 1

        extensions[suffix][0] += size
        extensions[suffix][1] += 1

    def ordered(
        source: dict[
            str,
            list[int],
        ],
    ) -> list[
        tuple[int, int, str]
    ]:
        return sorted(
            (
                (
                    values[0],
                    values[1],
                    name,
                )
                for (
                    name,
                    values,
                ) in source.items()
            ),
            key=lambda row: (
                row[0],
                row[1],
                row[2],
            ),
            reverse=True,
        )

    print(
        "sdump authoritative candidate inventory"
    )

    print(
        f"profile: {PROFILE_ID}"
    )

    print(
        f"target: {RUNTIME_ROOT}"
    )

    print(
        f"candidates: {len(candidates)}"
    )

    print(
        f"candidate_bytes: {total_bytes}"
    )

    print(
        f"candidate_mib: {mib(total_bytes):.2f}"
    )

    print(
        f"skipped: {len(skipped)}"
    )

    print(
        f"failures: {len(failures)}"
    )

    print(
        f"symlinks: {len(symlinks)}"
    )

    print(
        f"inaccessible_candidates: {inaccessible}"
    )

    emit_group(
        "TOP-LEVEL ADMITTED BULK",
        ordered(
            top_level
        ),
        TOP_DIRECTORY_LIMIT,
    )

    emit_group(
        "DEPTH-2 ADMITTED BULK",
        ordered(
            depth_two
        ),
        TOP_DIRECTORY_LIMIT,
    )

    emit_group(
        "DEPTH-3 ADMITTED BULK",
        ordered(
            depth_three
        ),
        TOP_DIRECTORY_LIMIT,
    )

    emit_group(
        "ADMITTED EXTENSIONS",
        ordered(
            extensions
        ),
        TOP_EXTENSION_LIMIT,
    )

    print()
    print(
        "LARGEST ADMITTED FILES"
    )
    print()

    for (
        size,
        relative,
        suffix,
    ) in sorted(
        files,
        key=lambda row: (
            row[0],
            row[1],
        ),
        reverse=True,
    )[:TOP_FILE_LIMIT]:
        print(
            f"{mib(size):12.2f} MiB  "
            f"{suffix:16s}  "
            f"{relative}"
        )

    print()
    print(
        "SUMMARY"
    )
    print()

    print(
        json.dumps(
            {
                "profile": PROFILE_ID,
                "target": str(
                    RUNTIME_ROOT
                ),
                "candidates": len(
                    candidates
                ),
                "candidate_bytes": (
                    total_bytes
                ),
                "candidate_mib": round(
                    mib(
                        total_bytes
                    ),
                    2,
                ),
                "skipped": len(
                    skipped
                ),
                "failures": len(
                    failures
                ),
                "symlinks": len(
                    symlinks
                ),
                "inaccessible_candidates": (
                    inaccessible
                ),
                "scanner_stats": (
                    candidate_metadata(
                        stats
                    )
                ),
            },
            indent=2,
            default=str,
            sort_keys=True,
        )
    )

    if failures:
        return 2

    if inaccessible:
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
