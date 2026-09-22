from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STORAGE = ROOT / "storage"

UPLOADS = STORAGE / "uploads"
MODELS = STORAGE / "models"
VOICES = STORAGE / "voices"
EXPORTS = STORAGE / "exports"
REPORTS = STORAGE / "reports"


def ensure_storage() -> None:
    """
    Ensure all shared storage directories exist.
    """
    for directory in (
        STORAGE,
        UPLOADS,
        MODELS,
        VOICES,
        EXPORTS,
        REPORTS,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_project(project_id: str) -> dict[str, Path]:
    """
    Create and return the directory layout for one avatar project.
    """

    ensure_storage()

    project = {
        "root": MODELS / project_id,
        "uploads": UPLOADS / project_id,
        "voices": VOICES / project_id,
        "exports": EXPORTS / project_id,
        "reports": REPORTS / project_id,
    }

    for directory in project.values():
        directory.mkdir(parents=True, exist_ok=True)

    return project
