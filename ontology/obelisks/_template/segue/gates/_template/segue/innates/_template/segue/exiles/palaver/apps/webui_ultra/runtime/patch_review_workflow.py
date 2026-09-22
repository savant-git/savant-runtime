#!/usr/bin/env python3
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path("/root/savant-runtime")
STORE = ROOT / "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/state/patch_review"
PENDING = STORE / "pending"
APPLIED = STORE / "applied"
REJECTED = STORE / "rejected"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure() -> None:
    for p in [STORE, PENDING, APPLIED, REJECTED]:
        p.mkdir(parents=True, exist_ok=True)


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"id": path.stem, "error": "invalid_json", "detail": str(exc)}


def list_pending() -> list[dict[str, Any]]:
    _ensure()
    return [_read(p) for p in sorted(PENDING.glob("*.json"))]


def create(payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    _ensure()
    data: dict[str, Any] = {}
    if payload:
        data.update(payload)
    data.update(kwargs)
    data.setdefault("id", f"patch_{uuid.uuid4().hex}")
    data.setdefault("status", "pending")
    data.setdefault("created_at", _now())
    path = PENDING / f"{data['id']}.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


def apply_patch(patch_id: str, **kwargs: Any) -> dict[str, Any]:
    _ensure()
    src = PENDING / f"{patch_id}.json"
    if not src.exists():
        return {"id": patch_id, "status": "missing", "applied": False}
    data = _read(src)
    data.update(kwargs)
    data["status"] = "applied"
    data["applied"] = True
    data["applied_at"] = _now()
    dst = APPLIED / src.name
    dst.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    src.unlink()
    return data


def reject_patch(patch_id: str, reason: str = "", **kwargs: Any) -> dict[str, Any]:
    _ensure()
    src = PENDING / f"{patch_id}.json"
    if not src.exists():
        return {"id": patch_id, "status": "missing", "rejected": False}
    data = _read(src)
    data.update(kwargs)
    data["status"] = "rejected"
    data["rejected"] = True
    data["rejected_at"] = _now()
    data["reason"] = reason
    dst = REJECTED / src.name
    dst.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    src.unlink()
    return data
