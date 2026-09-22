from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


COMPACT_MAX_FILE_BYTES = (
    512
    * 1024
)

COMPACT_MAX_TOTAL_CONTENT_BYTES = (
    8
    * 1024
    * 1024
)

COMPACT_MAX_FILES = 100_000

_VALID_BUDGET_STRATEGIES = frozenset(
    {
        "path_order",
        "migration_priority",
    }
)


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
    budget_strategy: str = (
        "path_order"
    )
    critical_path_prefixes: tuple[
        str,
        ...,
    ] = ()
    priority_path_prefixes: tuple[
        str,
        ...,
    ] = ()
    deprioritized_path_fragments: tuple[
        str,
        ...,
    ] = ()
    priority_filenames: frozenset[
        str
    ] = frozenset()
    recent_window_days: int = 30
    very_recent_window_days: int = 7
    small_file_bonus_bytes: int = (
        64
        * 1024
    )
    metadata_only_on_budget_exhaustion: bool = (
        True
    )

    def __post_init__(
        self,
    ) -> None:
        if (
            self.budget_strategy
            not in _VALID_BUDGET_STRATEGIES
        ):
            raise ValueError(
                "unsupported budget strategy: "
                f"{self.budget_strategy}"
            )

        numeric_fields = {
            "max_file_bytes":
                self.max_file_bytes,
            "max_total_content_bytes":
                self.max_total_content_bytes,
            "max_files":
                self.max_files,
            "recent_window_days":
                self.recent_window_days,
            "very_recent_window_days":
                self.very_recent_window_days,
            "small_file_bonus_bytes":
                self.small_file_bonus_bytes,
        }

        for (
            name,
            value,
        ) in numeric_fields.items():
            if (
                not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    "profile field "
                    f"{name!r} must be a "
                    "non-negative integer"
                )

        if self.max_file_bytes < 1:
            raise ValueError(
                "max_file_bytes must "
                "be positive"
            )

        if (
            self.max_total_content_bytes
            < 1
        ):
            raise ValueError(
                "max_total_content_bytes "
                "must be positive"
            )

        if self.max_files < 1:
            raise ValueError(
                "max_files must be positive"
            )

        if (
            self.very_recent_window_days
            > self.recent_window_days
        ):
            raise ValueError(
                "very_recent_window_days "
                "cannot exceed "
                "recent_window_days"
            )

        if (
            self.id.casefold()
            != "compact"
        ):
            return

        object.__setattr__(
            self,
            "max_file_bytes",
            min(
                self.max_file_bytes,
                COMPACT_MAX_FILE_BYTES,
            ),
        )

        object.__setattr__(
            self,
            "max_total_content_bytes",
            min(
                self.max_total_content_bytes,
                COMPACT_MAX_TOTAL_CONTENT_BYTES,
            ),
        )

        object.__setattr__(
            self,
            "max_files",
            min(
                self.max_files,
                COMPACT_MAX_FILES,
            ),
        )


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
    rendered_sha256: (
        str
        | None
    )
    content_id: (
        str
        | None
    )
    duplicate_of: (
        str
        | None
    )
    encoding: (
        str
        | None
    )
    redactions: int
    authoritative: bool
    included: bool
    reason: (
        str
        | None
    )
    source_kind: str = (
        "regular_file"
    )
    migration_priority: (
        int
        | None
    ) = None

    def to_dict(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return asdict(
            self
        )


@dataclass
class SkipRecord:
    path: str
    reason: str
    size: (
        int
        | None
    ) = None

    def to_dict(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return asdict(
            self
        )


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
    metadata_only_files: int = 0
    budget_excluded_files: int = 0
    budget_bytes_limit: int = 0
    budget_bytes_used: int = 0
    budget_bytes_remaining: int = 0
    priority_strategy: str = (
        "path_order"
    )

    def to_dict(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return asdict(
            self
        )


@dataclass
class Projection:
    records: list[
        FileRecord
    ]
    skipped: list[
        SkipRecord
    ]
    failures: list[
        SkipRecord
    ]
    symlinks: list[
        dict[
            str,
            Any,
        ]
    ]
    stats: ScanStats
    content_store: Path
    snapshot_hash: str
    unique_content_paths: dict[
        str,
        Path,
    ] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class UploadResult:
    uploaded: bool
    verified: bool
    bucket: (
        str
        | None
    )
    key: (
        str
        | None
    )
    uri: (
        str
        | None
    )
    size: (
        int
        | None
    )
    sha256: (
        str
        | None
    )
    etag: (
        str
        | None
    )
    version_id: (
        str
        | None
    )
    reason: (
        str
        | None
    )

    def to_dict(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return asdict(
            self
        )
