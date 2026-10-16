from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Profile:
    id: str
    description: str
    include_extensions: frozenset[str]
    include_filenames: frozenset[str]
    canon_path_names: frozenset[str]
    exclude_dir_names: frozenset[str]
    exclude_file_names: frozenset[str]
    exclude_extensions: frozenset[str]
    exclude_patterns: tuple[str, ...]
    secret_file_patterns: tuple[str, ...]
    max_file_bytes: int
    max_total_content_bytes: int
    max_files: int
    include_tree: bool = False
    include_inventory: bool = False
    respect_gitignore: bool = True
    redact_secrets: bool = True
    follow_symlinks: bool = False


@dataclass(frozen=True)
class Candidate:
    absolute_path: Path
    relative_path: str
    target_id: str
    category: str
    mode: int
    size: int
    mtime_ns: int
    inode: int
    device: int


@dataclass
class FileRecord:
    path: str
    target_id: str
    category: str
    language: str
    size: int
    mode: str
    mtime_ns: int
    source_sha256: str
    rendered_sha256: str | None
    content_id: str | None
    duplicate_of: str | None
    encoding: str | None
    redactions: int
    authoritative: bool
    included: bool
    reason: str | None
    source_kind: str = "regular_file"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SkipRecord:
    path: str
    reason: str
    size: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScanStats:
    directories_seen: int = 0
    files_seen: int = 0
    symlinks_seen: int = 0
    candidates: int = 0
    included_files: int = 0
    unique_contents: int = 0
    duplicate_files: int = 0
    source_bytes: int = 0
    rendered_bytes: int = 0
    duplicate_bytes_avoided: int = 0
    redactions: int = 0
    skipped: int = 0
    failures: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Projection:
    records: list[FileRecord]
    skipped: list[SkipRecord]
    failures: list[SkipRecord]
    symlinks: list[dict[str, Any]]
    stats: ScanStats
    content_store: Path
    snapshot_hash: str
    unique_content_paths: dict[str, Path] = field(default_factory=dict)


@dataclass(frozen=True)
class UploadResult:
    uploaded: bool
    verified: bool
    bucket: str | None
    key: str | None
    uri: str | None
    size: int | None
    sha256: str | None
    etag: str | None
    version_id: str | None
    reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
