#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


schema_version = (
    "savant.assurance."
    "attach-atlas-navigation.v1"
)

authority_effect = "none"

assets_root = Path(
    "/root/savant-runtime"
    "/ontology/obelisks/_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/niche/apps/taskboard/assets"
)

candidate_names = (
    "index.html",
    "app.html",
    "taskboard.html",
)

atlas_href = "/atlas/"
atlas_label = "atlas"

html_patterns = (
    re.compile(
        r'(?P<indent>^[ \t]*)'
        r'<a\b(?P<attrs>[^>]*)'
        r'href=["\']/(?P<route>masterplan|tasks|taskboard)/?["\']'
        r'(?P<tail>[^>]*)>'
        r'(?P<label>.*?)'
        r'</a>',
        re.IGNORECASE
        | re.MULTILINE
        | re.DOTALL,
    ),
    re.compile(
        r'(?P<indent>^[ \t]*)'
        r'<button\b(?P<attrs>[^>]*)'
        r'data-(?:route|view|surface)=["\']'
        r'(?P<route>masterplan|tasks|taskboard)'
        r'["\'](?P<tail>[^>]*)>'
        r'(?P<label>.*?)'
        r'</button>',
        re.IGNORECASE
        | re.MULTILINE
        | re.DOTALL,
    ),
)


class MigrationError(RuntimeError):
    pass


def atomic_write(
    path: Path,
    text: str,
) -> None:
    mode = path.stat().st_mode

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
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(
            temporary_path,
            mode,
        )

        os.replace(
            temporary_path,
            path,
        )

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def candidate_files() -> list[Path]:
    if not assets_root.is_dir():
        raise MigrationError(
            "Niche taskboard assets directory unavailable"
        )

    preferred = [
        assets_root / name
        for name in candidate_names
        if (assets_root / name).is_file()
    ]

    html_files = sorted(
        path
        for path in assets_root.rglob("*.html")
        if path.is_file()
        and path not in preferred
    )

    return preferred + html_files


def contains_atlas_entry(
    text: str,
) -> bool:
    href_pattern = re.compile(
        r'href=["\']/atlas/?["\']',
        re.IGNORECASE,
    )

    route_pattern = re.compile(
        r'data-(?:route|view|surface)=["\']atlas["\']',
        re.IGNORECASE,
    )

    return bool(
        href_pattern.search(text)
        or route_pattern.search(text)
    )


def render_anchor_entry(
    match: re.Match[str],
) -> str:
    source = match.group(0)

    indentation = match.group(
        "indent"
    )

    if source.lstrip().lower().startswith(
        "<a"
    ):
        return (
            source
            + "\n"
            + indentation
            + '<a href="/atlas/" '
            + 'data-savant-surface="atlas">'
            + atlas_label
            + "</a>"
        )

    return (
        source
        + "\n"
        + indentation
        + '<a href="/atlas/" '
        + 'data-savant-surface="atlas">'
        + atlas_label
        + "</a>"
    )


def locate_target() -> tuple[
    Path,
    str,
    re.Pattern[str],
    re.Match[str],
]:
    files = candidate_files()

    if not files:
        raise MigrationError(
            "no Niche taskboard HTML surface found"
        )

    already_installed: list[
        tuple[
            Path,
            str,
        ]
    ] = []

    anchors: list[
        tuple[
            Path,
            str,
            re.Pattern[str],
            re.Match[str],
        ]
    ] = []

    for path in files:
        text = path.read_text(
            encoding="utf-8"
        )

        if contains_atlas_entry(text):
            already_installed.append(
                (
                    path,
                    text,
                )
            )

            continue

        matches = []

        for pattern in html_patterns:
            matches.extend(
                (
                    pattern,
                    match,
                )
                for match
                in pattern.finditer(text)
            )

        if len(matches) == 1:
            pattern, match = matches[0]

            anchors.append(
                (
                    path,
                    text,
                    pattern,
                    match,
                )
            )

    if len(already_installed) == 1:
        path, text = already_installed[0]

        return (
            path,
            text,
            html_patterns[0],
            None,
        )

    if len(already_installed) > 1:
        raise MigrationError(
            "Atlas navigation already appears in multiple "
            "taskboard HTML surfaces"
        )

    if len(anchors) != 1:
        raise MigrationError(
            "Niche navigation anchor is ambiguous: "
            f"{len(anchors)} candidate surfaces"
        )

    return anchors[0]


def validate_result(
    text: str,
) -> None:
    atlas_href_count = len(
        re.findall(
            r'href=["\']/atlas/?["\']',
            text,
            re.IGNORECASE,
        )
    )

    atlas_marker_count = len(
        re.findall(
            r'data-savant-surface=["\']atlas["\']',
            text,
            re.IGNORECASE,
        )
    )

    if atlas_href_count != 1:
        raise MigrationError(
            "Atlas navigation href missing or duplicated: "
            f"{atlas_href_count}"
        )

    if atlas_marker_count != 1:
        raise MigrationError(
            "Atlas navigation marker missing or duplicated: "
            f"{atlas_marker_count}"
        )

    if "<html" not in text.lower():
        raise MigrationError(
            "target no longer resembles an HTML document"
        )


def migrate(
    apply: bool,
) -> dict[str, Any]:
    (
        target_path,
        original,
        _pattern,
        match,
    ) = locate_target()

    if match is None:
        validate_result(
            original
        )

        return {
            "schema":
                schema_version,
            "authority_effect":
                authority_effect,
            "status":
                "passed",
            "apply":
                apply,
            "changed":
                False,
            "owner":
                "exile:niche",
            "projection_only":
                True,
            "mutation_authority_added":
                False,
            "target":
                str(target_path),
            "disposition":
                "atlas_navigation_already_present",
            "route":
                atlas_href,
        }

    replacement = render_anchor_entry(
        match
    )

    migrated = (
        original[:match.start()]
        + replacement
        + original[match.end():]
    )

    validate_result(
        migrated
    )

    changed = (
        migrated != original
    )

    if apply and changed:
        atomic_write(
            target_path,
            migrated,
        )

        try:
            validate_result(
                target_path.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            atomic_write(
                target_path,
                original,
            )

            raise

    return {
        "schema":
            schema_version,
        "authority_effect":
            authority_effect,
        "status":
            "passed",
        "apply":
            apply,
        "changed":
            changed,
        "owner":
            "exile:niche",
        "projection_only":
            True,
        "mutation_authority_added":
            False,
        "target":
            str(target_path),
        "disposition":
            (
                "atlas_navigation_installed"
                if changed
                else
                "atlas_navigation_already_present"
            ),
        "route":
            atlas_href,
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    arguments = parser.parse_args()

    try:
        result = migrate(
            arguments.apply
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema":
                        schema_version,
                    "authority_effect":
                        authority_effect,
                    "status":
                        "failed",
                    "apply":
                        arguments.apply,
                    "error":
                        str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )

        return 1

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
