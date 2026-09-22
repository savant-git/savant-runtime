from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Iterable

from .model import Profile
from .util import is_within


class IgnoreMatcher:
    def __init__(
        self,
        profile: Profile,
        target_root: Path,
        absolute_excluded_roots: Iterable[Path] = (),
        include_hidden: bool = False,
        include_secrets: bool = False,
        extra_patterns: Iterable[str] = (),
        respect_gitignore: bool | None = None,
    ) -> None:
        self.profile = profile
        self.target_root = target_root.resolve(strict=False)
        self.absolute_excluded_roots = tuple(
            root.resolve(strict=False) for root in absolute_excluded_roots
        )
        self.include_hidden = include_hidden
        self.include_secrets = include_secrets
        self.patterns = list(profile.exclude_patterns)
        self.patterns.extend(extra_patterns)
        should_read_gitignore = (
            profile.respect_gitignore if respect_gitignore is None else respect_gitignore
        )
        for ignore_name in (".sdumpignore", ".gitignore"):
            if ignore_name == ".gitignore" and not should_read_gitignore:
                continue
            path = self.target_root / ignore_name
            if path.is_file():
                self.patterns.extend(self._read_ignore_file(path))
        self._pathspec = self._build_pathspec(self.patterns)

    @staticmethod
    def _read_ignore_file(path: Path) -> list[str]:
        lines: list[str] = []
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            lines.append(line)
        return lines

    @staticmethod
    def _build_pathspec(patterns: list[str]):
        try:
            import pathspec

            return pathspec.GitIgnoreSpec.from_lines(patterns)
        except Exception:
            return None

    @staticmethod
    def _hidden(relative_path: str) -> bool:
        return any(part.startswith(".") and part not in {".", ".."} for part in Path(relative_path).parts)

    def _pattern_match(self, relative_path: str, is_dir: bool) -> bool:
        path = relative_path.replace("\\", "/").lstrip("./")
        candidate = f"{path}/" if is_dir and path and not path.endswith("/") else path
        if self._pathspec is not None:
            return bool(self._pathspec.match_file(candidate))

        ignored = False
        for raw_pattern in self.patterns:
            pattern = raw_pattern.strip()
            if not pattern or pattern.startswith("#"):
                continue
            negate = pattern.startswith("!")
            if negate:
                pattern = pattern[1:]
            anchored = pattern.startswith("/")
            pattern = pattern.lstrip("/")
            names = [candidate, path, Path(path).name]
            matched = any(fnmatch.fnmatch(name, pattern) for name in names)
            if not matched and not anchored:
                matched = fnmatch.fnmatch(candidate, f"**/{pattern}")
            if matched:
                ignored = not negate
        return ignored

    def secret_filename(self, relative_path: str) -> bool:
        name = Path(relative_path).name.casefold()
        path = relative_path.casefold()
        for pattern in self.profile.secret_file_patterns:
            lowered = pattern.casefold()
            if fnmatch.fnmatch(name, lowered) or fnmatch.fnmatch(path, lowered):
                return True
        return False

    def skip_reason(self, absolute_path: Path, relative_path: str, is_dir: bool) -> str | None:
        absolute = absolute_path.resolve(strict=False)
        if any(is_within(absolute, root) for root in self.absolute_excluded_roots):
            return "excluded_absolute_root"

        name = absolute_path.name.casefold()
        suffix = absolute_path.suffix.casefold()

        if is_dir and name in self.profile.exclude_dir_names:
            return "excluded_directory_name"
        if not is_dir and name in self.profile.exclude_file_names:
            return "excluded_file_name"
        if not is_dir and suffix in self.profile.exclude_extensions:
            return "excluded_extension"
        if not self.include_hidden and self._hidden(relative_path):
            return "hidden_path"
        if not is_dir and not self.include_secrets and self.secret_filename(relative_path):
            return "secret_filename"
        if self._pattern_match(relative_path, is_dir):
            return "excluded_pattern"
        return None
