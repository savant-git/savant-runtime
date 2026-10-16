from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .model import UploadResult
from .util import atomic_write_json, now_iso, now_stamp, stable_hash


def write_receipt(
    receipt_root: Path,
    artifact: Path,
    artifact_sha256: str,
    snapshot_hash: str,
    profile: str,
    counts: Mapping[str, Any],
    upload: UploadResult,
    local_deleted: bool,
) -> Path:
    payload: dict[str, Any] = {
        "schema": "savant.sdump.receipt.v3",
        "tool": "sdump-enterprise",
        "profile": profile,
        "snapshot_hash": snapshot_hash,
        "artifact": {
            "name": artifact.name,
            "local_path": str(artifact),
            "size": upload.size if upload.size is not None else artifact.stat().st_size,
            "sha256": artifact_sha256,
            "local_deleted": local_deleted,
        },
        "remote": upload.to_dict(),
        "counts": dict(counts),
        "completed_at": now_iso(),
    }
    payload["deterministic_hash"] = stable_hash(
        {key: value for key, value in payload.items() if key not in {"completed_at", "deterministic_hash"}}
    )
    receipt_root.mkdir(parents=True, exist_ok=True)
    path = receipt_root / f"{now_stamp()}__{artifact_sha256[:16]}__{artifact.name}.json"
    atomic_write_json(path, payload)
    return path
