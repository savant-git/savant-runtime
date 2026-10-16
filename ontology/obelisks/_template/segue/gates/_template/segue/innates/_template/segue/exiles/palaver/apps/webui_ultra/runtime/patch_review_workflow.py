#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path('/root/savant-runtime')
STORE = ROOT / 'ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/state/patch_review'
PENDING = STORE / 'pending'
APPLIED = STORE / 'applied'
REJECTED = STORE / 'rejected'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure() -> None:
    for path in (STORE, PENDING, APPLIED, REJECTED):
        path.mkdir(parents=True, exist_ok=True)


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('proposal must be an object')
        return value
    except (OSError, ValueError) as exc:
        return {'id': path.stem, 'error': 'invalid_json', 'detail': str(exc)}


def _digest(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def _target(relative: str) -> Path:
    if not isinstance(relative, str) or not relative or '\x00' in relative:
        raise ValueError('invalid source path')
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('source path must be relative to runtime')
    target = ROOT / path
    if not target.resolve(strict=False).is_relative_to(ROOT.resolve()):
        raise ValueError('source path escapes runtime')
    cursor = ROOT
    for part in path.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError('symbolic links are not permitted')
    if target.exists() and not target.is_file():
        raise ValueError('source target is not a regular file')
    return target


def _id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'patch_[0-9a-f]{32}', value):
        raise ValueError('invalid patch identifier')
    return value


def list_pending() -> list[dict[str, Any]]:
    _ensure()
    return [_read(path) for path in sorted(PENDING.glob('*.json'))]


def create(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Accept the existing payload API and server_native's four-argument API."""
    _ensure()
    if len(args) == 4:
        relative, before, after, diff = args
        data = {'path': relative, 'before': before, 'after': after, 'diff': diff}
    elif len(args) == 1 and isinstance(args[0], dict):
        data = dict(args[0])
    elif not args:
        data = {}
    else:
        raise TypeError('create expects a payload or path, before, after, diff')
    data.update(kwargs)
    relative = data.get('path')
    before = data.get('before')
    after = data.get('after')
    if not isinstance(before, str) or not isinstance(after, str):
        raise ValueError('proposal requires complete before and after text')
    target = _target(relative)
    current = target.read_text(encoding='utf-8') if target.exists() else ''
    if current != before:
        raise ValueError('source changed before proposal creation')
    data['id'] = f'patch_{uuid.uuid4().hex}'
    data['status'] = 'pending'
    data['created_at'] = _now()
    data['before_sha256'] = _digest(before)
    data['after_sha256'] = _digest(after)
    destination = PENDING / f"{data['id']}.json"
    with destination.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write('\n')
    return data


def apply_patch(patch_id: str, **kwargs: Any) -> dict[str, Any]:
    _ensure()
    patch_id = _id(patch_id)
    src = PENDING / f'{patch_id}.json'
    if not src.is_file():
        return {'id': patch_id, 'status': 'missing', 'applied': False}
    data = _read(src)
    if 'error' in data:
        raise ValueError('invalid pending proposal')
    target = _target(data.get('path'))
    before, after = data.get('before'), data.get('after')
    if not isinstance(before, str) or not isinstance(after, str):
        raise ValueError('proposal is missing source content')
    if data.get('before_sha256') != _digest(before) or data.get('after_sha256') != _digest(after):
        raise ValueError('proposal integrity mismatch')
    current = target.read_text(encoding='utf-8') if target.exists() else ''
    if current != before:
        return {'id': patch_id, 'status': 'stale', 'applied': False}
    if not target.parent.is_dir():
        raise ValueError('target parent directory does not exist')
    # Preserve the original mode and atomically replace within the same directory.
    mode = target.stat().st_mode & 0o777 if target.exists() else 0o644
    fd, temporary = tempfile.mkstemp(prefix='.palaver-', dir=target.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(after)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        # Archive before changing source; a failed archive leaves source untouched.
        result = dict(data)
        result.update(kwargs)
        result.update(status='applied', applied=True, applied_at=_now())
        dst = APPLIED / src.name
        with dst.open('x', encoding='utf-8') as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write('\n')
        os.replace(temporary, target)
        src.unlink()
        return result
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def reject_patch(patch_id: str, reason: str = '', **kwargs: Any) -> dict[str, Any]:
    _ensure()
    patch_id = _id(patch_id)
    src = PENDING / f'{patch_id}.json'
    if not src.is_file():
        return {'id': patch_id, 'status': 'missing', 'rejected': False}
    data = _read(src)
    if 'error' in data:
        raise ValueError('invalid pending proposal')
    data.update(kwargs)
    data.update(status='rejected', rejected=True, rejected_at=_now(), reason=reason)
    dst = REJECTED / src.name
    with dst.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write('\n')
    src.unlink()
    return data
