#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Any, Mapping


SAVANT_ROOT = Path(
    os.environ.get(
        "SAVANT_ROOT",
        "/root/savant-runtime",
    )
).expanduser().absolute()


KNOWN_RUNTIME_ROOTS = frozenset({
    "authority_graph",
    "bin",
    "canon",
    "canon-system",
    "ontology",
    "runtime",
    "sessions",
    "tests",
    "tools",
    "vault",
    "webui-nextgen",
    "webui_ultra",
})


SCHEME_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z0-9+.-]*:"
)

WINDOWS_DRIVE_PATTERN = re.compile(
    r"^[A-Za-z]:[\\/]"
)


@dataclass(
    frozen=True,
    slots=True,
)
class ReferenceResolution:
    original: str
    canonical: str
    kind: str
    matched_path: str | None = None

    @property
    def changed(
        self,
    ) -> bool:
        return (
            self.original
            != self.canonical
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "original": self.original,
            "canonical": self.canonical,
            "kind": self.kind,
            "matched_path": (
                self.matched_path
            ),
            "changed": self.changed,
        }


def _absolute_lexical(
    path: Path | str,
) -> Path:
    return Path(
        os.path.abspath(
            os.path.expanduser(
                str(path)
            )
        )
    )


def _relative_to_root(
    path: Path | str,
    root: Path | str,
) -> Path | None:
    absolute_root = (
        _absolute_lexical(
            root
        )
    )

    absolute_path = (
        _absolute_lexical(
            path
        )
    )

    try:
        return (
            absolute_path
            .relative_to(
                absolute_root
            )
        )
    except ValueError:
        return None


def filesystem_reference_id(
    path: Path | str,
    *,
    root: Path | str = SAVANT_ROOT,
) -> str:
    relative = _relative_to_root(
        path,
        root,
    )

    if relative is None:
        raise ValueError(
            "filesystem path is outside "
            f"the Savant root: {path}"
        )

    if str(relative) in {
        "",
        ".",
    }:
        return "fs:."

    return (
        "fs:"
        + relative.as_posix()
    )


def _looks_like_scheme(
    value: str,
) -> bool:
    if WINDOWS_DRIVE_PATTERN.match(
        value
    ):
        return False

    return bool(
        SCHEME_PATTERN.match(
            value
        )
    )


def _source_directory(
    source_path: Path | str | None,
    *,
    root: Path,
) -> Path | None:
    if source_path is None:
        return None

    raw = str(
        source_path
    ).strip()

    if not raw:
        return None

    candidate = Path(
        raw
    ).expanduser()

    if not candidate.is_absolute():
        candidate = (
            root
            / candidate
        )

    candidate = _absolute_lexical(
        candidate
    )

    if (
        candidate.exists()
        and candidate.is_dir()
    ):
        return candidate

    return candidate.parent


def source_path_from_context(
    provenance: Mapping[
        str,
        Any,
    ] | None,
    metadata: Mapping[
        str,
        Any,
    ] | None,
) -> str | None:
    metadata_value = dict(
        metadata
        or {}
    )

    provenance_value = dict(
        provenance
        or {}
    )

    direct = metadata_value.get(
        "source_path"
    )

    if (
        isinstance(
            direct,
            str,
        )
        and direct.strip()
    ):
        return direct.strip()

    for key in (
        "source_files",
        "created_from",
    ):
        values = provenance_value.get(
            key
        )

        if isinstance(
            values,
            str,
        ):
            values = [
                values
            ]

        if not isinstance(
            values,
            list,
        ):
            continue

        for value in values:
            if (
                isinstance(
                    value,
                    str,
                )
                and value.strip()
            ):
                return value.strip()

    return None


def resolve_reference(
    reference: str,
    *,
    root: Path | str = SAVANT_ROOT,
    source_path: Path | str | None = None,
) -> ReferenceResolution:
    original = str(
        reference
    ).strip()

    if not original:
        return ReferenceResolution(
            original=original,
            canonical=original,
            kind="empty",
        )

    if original.startswith(
        "fs:"
    ):
        return ReferenceResolution(
            original=original,
            canonical=original,
            kind="filesystem_id",
        )

    runtime_root = (
        _absolute_lexical(
            root
        )
    )

    expanded = Path(
        original
    ).expanduser()

    if expanded.is_absolute():
        relative = _relative_to_root(
            expanded,
            runtime_root,
        )

        if relative is not None:
            matched = (
                runtime_root
                / relative
            )

            return ReferenceResolution(
                original=original,
                canonical=(
                    filesystem_reference_id(
                        matched,
                        root=runtime_root,
                    )
                ),
                kind="filesystem_absolute",
                matched_path=str(
                    matched
                ),
            )

        return ReferenceResolution(
            original=original,
            canonical=original,
            kind="external_filesystem",
            matched_path=str(
                _absolute_lexical(
                    expanded
                )
            ),
        )

    if _looks_like_scheme(
        original
    ):
        return ReferenceResolution(
            original=original,
            canonical=original,
            kind="semantic",
        )

    normalized_text = (
        original.replace(
            "\\",
            "/",
        )
    )

    root_name_prefix = (
        runtime_root.name
        + "/"
    )

    if normalized_text == (
        runtime_root.name
    ):
        return ReferenceResolution(
            original=original,
            canonical="fs:.",
            kind="filesystem_root_name",
            matched_path=str(
                runtime_root
            ),
        )

    if normalized_text.startswith(
        root_name_prefix
    ):
        candidate = (
            runtime_root.parent
            / normalized_text
        )

        relative = _relative_to_root(
            candidate,
            runtime_root,
        )

        if relative is not None:
            return ReferenceResolution(
                original=original,
                canonical=(
                    filesystem_reference_id(
                        candidate,
                        root=runtime_root,
                    )
                ),
                kind=(
                    "filesystem_root_prefixed"
                ),
                matched_path=str(
                    _absolute_lexical(
                        candidate
                    )
                ),
            )

    relative_path = Path(
        normalized_text
    )

    explicit_relative = (
        normalized_text.startswith(
            "./"
        )
        or normalized_text.startswith(
            "../"
        )
    )

    path_shaped = (
        "/" in normalized_text
        or bool(
            relative_path.suffix
        )
    )

    source_directory = (
        _source_directory(
            source_path,
            root=runtime_root,
        )
    )

    if (
        source_directory is not None
        and (
            explicit_relative
            or path_shaped
        )
    ):
        source_candidate = (
            source_directory
            / relative_path
        )

        source_relative = (
            _relative_to_root(
                source_candidate,
                runtime_root,
            )
        )

        if (
            source_relative is not None
            and source_candidate.exists()
        ):
            return ReferenceResolution(
                original=original,
                canonical=(
                    filesystem_reference_id(
                        source_candidate,
                        root=runtime_root,
                    )
                ),
                kind=(
                    "filesystem_source_relative"
                ),
                matched_path=str(
                    _absolute_lexical(
                        source_candidate
                    )
                ),
            )

    root_candidate = (
        runtime_root
        / relative_path
    )

    root_relative = (
        _relative_to_root(
            root_candidate,
            runtime_root,
        )
    )

    first_part = (
        relative_path.parts[0]
        if relative_path.parts
        else ""
    )

    recognized_root = (
        first_part
        in KNOWN_RUNTIME_ROOTS
    )

    if (
        root_relative is not None
        and (
            root_candidate.exists()
            or recognized_root
        )
    ):
        return ReferenceResolution(
            original=original,
            canonical=(
                filesystem_reference_id(
                    root_candidate,
                    root=runtime_root,
                )
            ),
            kind=(
                "filesystem_runtime_relative"
            ),
            matched_path=str(
                _absolute_lexical(
                    root_candidate
                )
            ),
        )

    return ReferenceResolution(
        original=original,
        canonical=original,
        kind="semantic",
    )


def normalize_reference(
    reference: str,
    *,
    root: Path | str = SAVANT_ROOT,
    source_path: Path | str | None = None,
) -> str:
    return resolve_reference(
        reference,
        root=root,
        source_path=source_path,
    ).canonical
