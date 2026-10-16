from __future__ import annotations

import difflib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from coda_bridge import current_digest
from coda_bridge import save_file


ROOT = Path(
    "/root/savant-runtime"
).resolve()

PALAVER_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver"
)

LEGACY_WORKFLOW = (
    PALAVER_ROOT
    / "apps"
    / "webui_ultra"
    / "runtime"
    / "patch_review_workflow.py"
)

WORKFLOW_MODULE_NAME = (
    "palaver_patch_review_compat"
)


def load_workflow() -> ModuleType:
    existing = sys.modules.get(
        WORKFLOW_MODULE_NAME
    )

    if existing is not None:
        return existing

    if not LEGACY_WORKFLOW.is_file():
        raise RuntimeError(
            "Palaver patch-review workflow missing: "
            f"{LEGACY_WORKFLOW}"
        )

    spec = (
        importlib.util
        .spec_from_file_location(
            WORKFLOW_MODULE_NAME,
            LEGACY_WORKFLOW,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "unable to load Palaver "
            "patch-review workflow"
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        WORKFLOW_MODULE_NAME
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def safe_target(
    path: str,
) -> tuple[
    Path,
    str,
]:
    value = str(
        path
        or ""
    ).strip().lstrip("/")

    if not value:
        raise RuntimeError(
            "patch path is required"
        )

    target = (
        ROOT
        / value
    ).resolve()

    if not (
        target == ROOT
        or ROOT in target.parents
    ):
        raise RuntimeError(
            "patch path escapes Savant root"
        )

    relative = str(
        target.relative_to(
            ROOT
        )
    )

    return (
        target,
        relative,
    )


def create_review(
    path: str,
    after: str,
) -> dict[str, Any]:
    workflow = load_workflow()

    target, relative = safe_target(
        path
    )

    before = ""

    if target.exists():
        if not target.is_file():
            raise RuntimeError(
                "patch target is not a file"
            )

        before = target.read_text(
            encoding="utf-8",
            errors="replace",
        )

    proposed = str(
        after
    )

    diff = "".join(
        difflib.unified_diff(
            before.splitlines(
                True
            ),
            proposed.splitlines(
                True
            ),
            fromfile=(
                "before/"
                + relative
            ),
            tofile=(
                "after/"
                + relative
            ),
        )
    )

    payload = {
        "path": relative,
        "before": before,
        "after": proposed,
        "diff": diff,
        "expected_digest": current_digest(
            relative
        ),
        "mutation_owner": "coda",
        "requester": "palaver",
        "status": "pending",
    }

    return workflow.create(
        payload
    )


def apply_review(
    patch_id: str,
) -> dict[str, Any]:
    workflow = load_workflow()

    patch_id = str(
        patch_id
        or ""
    ).strip()

    if not patch_id:
        raise RuntimeError(
            "patch_id is required"
        )

    pending = {
        str(
            item.get(
                "id"
            )
        ): item
        for item in workflow.list_pending()
        if isinstance(
            item,
            dict,
        )
    }

    data = pending.get(
        patch_id
    )

    if data is None:
        return {
            "id": patch_id,
            "status": "missing",
            "applied": False,
            "detail": (
                "pending patch not found"
            ),
        }

    if data.get(
        "error"
    ):
        raise RuntimeError(
            "pending patch record is invalid"
        )

    path = str(
        data.get(
            "path"
        )
        or ""
    )

    if not path:
        raise RuntimeError(
            "pending patch has no path"
        )

    if "after" not in data:
        raise RuntimeError(
            "pending patch has no after content"
        )

    expected_digest = data.get(
        "expected_digest"
    )

    mutation = save_file(
        path,
        str(
            data["after"]
        ),
        expected_digest=(
            str(
                expected_digest
            )
            if expected_digest
            is not None
            else None
        ),
        intent=(
            "Palaver approved "
            f"patch-review {patch_id}"
        ),
    )

    applied = workflow.apply_patch(
        patch_id,
        mutation_owner="coda",
        mutation_receipt_id=(
            mutation.get(
                "receipt_id"
            )
        ),
        mutation_receipt=(
            mutation.get(
                "receipt"
            )
        ),
        after_digest=(
            mutation.get(
                "after_digest"
            )
        ),
    )

    applied[
        "mutation"
    ] = mutation

    return applied


def reject_review(
    patch_id: str,
    reason: str = "",
) -> dict[str, Any]:
    workflow = load_workflow()

    return workflow.reject_patch(
        patch_id,
        reason=reason,
    )


def list_pending() -> list[dict[str, Any]]:
    workflow = load_workflow()

    return workflow.list_pending()


def integration_status() -> dict[str, Any]:
    return {
        "owner": "palaver",
        "review_owner": "palaver",
        "mutation_owner": "coda",
        "optimistic_concurrency": True,
        "receipt_required_on_apply": True,
        "authority_effect": "none",
    }
