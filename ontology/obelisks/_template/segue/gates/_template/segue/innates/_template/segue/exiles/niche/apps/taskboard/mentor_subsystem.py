from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA = "savant.niche.mentor.document.v1"
AUTHORITY_EFFECT = "none"


@dataclass(frozen=True)
class MentorPaths:
    app_root: Path
    mentor_root: Path
    masterplan: Path
    structure: Path
    combined: Path


class MentorSubsystem:
    """Niche-owned living projection of Savant's masterplan + structure."""

    def __init__(self, app_root: Path) -> None:
        app_root = Path(app_root).resolve()
        mentor_root = app_root / "assets/mentor"
        self.paths = MentorPaths(
            app_root=app_root,
            mentor_root=mentor_root,
            masterplan=mentor_root / "masterplan.md",
            structure=mentor_root / "structure.md",
            combined=mentor_root / "savant_mentor_current.md",
        )
        self._lock = threading.RLock()
        self._last_signature: tuple[tuple[int, int], tuple[int, int]] | None = None
        self._last_digest: str | None = None

    @staticmethod
    def _sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _revision(text: str) -> str:
        for line in text.splitlines()[:80]:
            lower = line.lower().strip()
            if lower.startswith("**document revision:**"):
                return line.split(":**", 1)[-1].strip().strip("`")
        return "unknown"

    @staticmethod
    def _signature(path: Path) -> tuple[int, int]:
        stat = path.stat()
        return stat.st_mtime_ns, stat.st_size

    def _source_signature(self) -> tuple[tuple[int, int], tuple[int, int]]:
        return (
            self._signature(self.paths.masterplan),
            self._signature(self.paths.structure),
        )

    def _read_sources(self) -> tuple[str, str]:
        if not self.paths.masterplan.is_file():
            raise FileNotFoundError(
                f"mentor masterplan source is absent: {self.paths.masterplan}"
            )
        if not self.paths.structure.is_file():
            raise FileNotFoundError(
                f"mentor structure source is absent: {self.paths.structure}"
            )
        return (
            self.paths.masterplan.read_text(encoding="utf-8"),
            self.paths.structure.read_text(encoding="utf-8"),
        )

    def _render(self, masterplan: str, structure: str) -> str:
        masterplan_bytes = masterplan.encode("utf-8")
        structure_bytes = structure.encode("utf-8")
        masterplan_digest = self._sha256(masterplan_bytes)
        structure_digest = self._sha256(structure_bytes)
        masterplan_revision = self._revision(masterplan)
        structure_revision = self._revision(structure)

        header = (
            "# savant mentor current\n\n"
            f"**projection schema:** `{SCHEMA}`  \n"
            "**projection owner:** `niche/mentor`  \n"
            "**authority effect:** `none`  \n"
            f"**masterplan revision:** `{masterplan_revision}`  \n"
            f"**masterplan sha256:** `{masterplan_digest}`  \n"
            f"**structure revision:** `{structure_revision}`  \n"
            f"**structure sha256:** `{structure_digest}`  \n\n"
            "> this file is a deterministic living projection. it combines the current "
            "mentor masterplan and structure sources for human and ai consumption. "
            "regeneration does not create, accept, supersede, or modify savant authority.\n\n"
            "---\n\n"
        )

        return (
            header
            + "# masterplan projection\n\n"
            + masterplan.rstrip()
            + "\n\n---\n\n"
            + "# structure projection\n\n"
            + structure.rstrip()
            + "\n"
        )

    @staticmethod
    def _write_atomic(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
            text=True,
        )
        temporary = Path(temporary_name)

        try:
            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())

            os.chmod(temporary, 0o644)
            os.replace(temporary, path)

            directory_fd = os.open(
                path.parent,
                os.O_RDONLY,
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary.exists():
                temporary.unlink()

    def refresh(
        self,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            signature = self._source_signature()

            needs_refresh = (
                force
                or self._last_signature != signature
                or not self.paths.combined.is_file()
            )

            if needs_refresh:
                masterplan, structure = self._read_sources()
                rendered = self._render(
                    masterplan,
                    structure,
                )
                digest = self._sha256(
                    rendered.encode("utf-8")
                )

                current_digest = None

                if self.paths.combined.is_file():
                    current_digest = self._sha256(
                        self.paths.combined.read_bytes()
                    )

                if current_digest != digest:
                    self._write_atomic(
                        self.paths.combined,
                        rendered,
                    )

                self._last_signature = signature
                self._last_digest = digest

            elif self._last_digest is None:
                self._last_digest = self._sha256(
                    self.paths.combined.read_bytes()
                )

            return self.status()

    def status(self) -> dict[str, Any]:
        masterplan, structure = self._read_sources()

        combined = (
            self.paths.combined.read_text(
                encoding="utf-8"
            )
            if self.paths.combined.is_file()
            else ""
        )

        return {
            "schema": SCHEMA,
            "ok": bool(combined),
            "authority_effect": AUTHORITY_EFFECT,
            "projection_only": True,
            "living": True,
            "owner": "niche/mentor",
            "masterplan": {
                "revision": self._revision(
                    masterplan
                ),
                "sha256": self._sha256(
                    masterplan.encode("utf-8")
                ),
                "bytes": len(
                    masterplan.encode("utf-8")
                ),
            },
            "structure": {
                "revision": self._revision(
                    structure
                ),
                "sha256": self._sha256(
                    structure.encode("utf-8")
                ),
                "bytes": len(
                    structure.encode("utf-8")
                ),
            },
            "combined": {
                "path": str(
                    self.paths.combined
                ),
                "sha256": (
                    self._sha256(
                        combined.encode("utf-8")
                    )
                    if combined
                    else None
                ),
                "bytes": len(
                    combined.encode("utf-8")
                ),
            },
        }

    def document(self) -> dict[str, Any]:
        status = self.refresh()

        text = self.paths.combined.read_text(
            encoding="utf-8"
        )

        return {
            **status,
            "document": text,
        }

    def source_document(
        self,
        kind: str,
    ) -> dict[str, Any]:
        kind = str(kind).strip().lower()

        if kind == "masterplan":
            path = self.paths.masterplan

        elif kind == "structure":
            path = self.paths.structure

        elif kind in {
            "mentor",
            "combined",
            "current",
        }:
            self.refresh()
            path = self.paths.combined
            kind = "mentor"

        else:
            raise ValueError(
                "mentor document kind must be "
                "masterplan, structure, or mentor"
            )

        text = path.read_text(
            encoding="utf-8"
        )

        return {
            "schema": SCHEMA,
            "ok": True,
            "authority_effect": AUTHORITY_EFFECT,
            "projection_only": True,
            "living": kind == "mentor",
            "kind": kind,
            "revision": self._revision(
                text
            ),
            "sha256": self._sha256(
                text.encode("utf-8")
            ),
            "bytes": len(
                text.encode("utf-8")
            ),
            "document": text,
        }
