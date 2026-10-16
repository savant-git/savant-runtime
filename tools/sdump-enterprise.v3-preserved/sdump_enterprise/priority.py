from __future__ import annotations

from pathlib import PurePosixPath

from .model import (
    Candidate,
    Profile,
)


_NANOSECONDS_PER_DAY = (
    86_400_000_000_000
)

_CODE_SUFFIXES = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".mts",
        ".cts",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".kts",
        ".c",
        ".cc",
        ".cpp",
        ".cxx",
        ".h",
        ".hh",
        ".hpp",
        ".hxx",
        ".cs",
        ".rb",
        ".php",
        ".lua",
        ".pl",
        ".r",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".sql",
    }
)

_CONFIG_SUFFIXES = frozenset(
    {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".xml",
        ".xsd",
        ".tf",
        ".tfvars",
        ".gradle",
        ".properties",
    }
)

_DOC_SUFFIXES = frozenset(
    {
        ".md",
        ".markdown",
        ".rst",
        ".txt",
    }
)

_TEST_FRAGMENTS = (
    "/tests/",
    "/test/",
    "/fixtures/",
    "/examples/",
    "/example/",
)


def _normalized(
    path: str,
) -> str:
    return (
        "/"
        + path.replace(
            "\\",
            "/",
        )
        .casefold()
        .strip(
            "/"
        )
        + "/"
    )


def _matches_prefix(
    path: str,
    prefixes: tuple[
        str,
        ...,
    ],
) -> bool:
    normalized = (
        path.replace(
            "\\",
            "/",
        )
        .casefold()
        .lstrip(
            "/"
        )
    )

    return any(
        normalized.startswith(
            prefix.replace(
                "\\",
                "/",
            )
            .casefold()
            .lstrip(
                "/"
            )
        )
        for prefix in prefixes
        if prefix
    )


def migration_priority(
    candidate: Candidate,
    profile: Profile,
    newest_mtime_ns: int,
) -> int:
    path = (
        candidate.relative_path
        .replace(
            "\\",
            "/",
        )
    )

    folded = _normalized(
        path
    )

    pure = PurePosixPath(
        path
    )

    suffix = (
        pure.suffix.casefold()
    )

    filename = (
        pure.name.casefold()
    )

    score = 0

    if _matches_prefix(
        path,
        profile.critical_path_prefixes,
    ):
        score += 10_000

    elif _matches_prefix(
        path,
        profile.priority_path_prefixes,
    ):
        score += 4_000

    if (
        candidate.category
        == "canon"
    ):
        score += 1_500
    else:
        score += 600

    if (
        filename
        in profile.priority_filenames
    ):
        score += 1_200

    if suffix in _CODE_SUFFIXES:
        score += 700

    elif (
        suffix
        in _CONFIG_SUFFIXES
    ):
        score += 500

    elif suffix in _DOC_SUFFIXES:
        score += 250

    if "/runtime/" in folded:
        score += 850

    if "/commands/" in folded:
        score += 500

    if "/registry/" in folded:
        score += 450

    if "/authority/" in folded:
        score += 700

    if (
        "/canon/" in folded
        or "/canon-system/" in folded
    ):
        score += 700

    if "/ontology/" in folded:
        score += 550

    if (
        "/contracts/" in folded
        or "/schema/" in folded
    ):
        score += 350

    age_ns = max(
        0,
        (
            newest_mtime_ns
            - candidate.mtime_ns
        ),
    )

    very_recent_ns = (
        profile.very_recent_window_days
        * _NANOSECONDS_PER_DAY
    )

    recent_ns = (
        profile.recent_window_days
        * _NANOSECONDS_PER_DAY
    )

    if (
        very_recent_ns
        and age_ns
        <= very_recent_ns
    ):
        score += 1_000

    elif (
        recent_ns
        and age_ns
        <= recent_ns
    ):
        score += 500

    if (
        profile.small_file_bonus_bytes
        and candidate.size
        <= profile.small_file_bonus_bytes
    ):
        score += 250

    if any(
        fragment in folded
        for fragment
        in _TEST_FRAGMENTS
    ):
        score -= 500

    for fragment in (
        profile
        .deprioritized_path_fragments
    ):
        normalized_fragment = (
            fragment.replace(
                "\\",
                "/",
            )
            .casefold()
        )

        if (
            normalized_fragment
            and normalized_fragment
            in folded
        ):
            score -= 1_500

    depth = len(
        pure.parts
    )

    score -= (
        min(
            depth,
            40,
        )
        * 3
    )

    return score


def priority_key(
    candidate: Candidate,
    profile: Profile,
    newest_mtime_ns: int,
) -> tuple[
    int,
    int,
    int,
    str,
]:
    score = migration_priority(
        candidate,
        profile,
        newest_mtime_ns,
    )

    return (
        -score,
        candidate.size,
        -candidate.mtime_ns,
        (
            candidate
            .relative_path
            .casefold()
        ),
    )
