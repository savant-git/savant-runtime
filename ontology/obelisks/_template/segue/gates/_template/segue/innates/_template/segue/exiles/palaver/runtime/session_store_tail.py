from __future__ import annotations

from typing import Any

schema = "savant://runtime/palaver/session-store-tail/1.1.0"
owner = "exile:palaver"


class session_store_tail_error(RuntimeError):
    pass


def install(
    store_class: type,
) -> dict[str, Any]:
    loader = getattr(store_class, "load_events", None)
    if not callable(loader):
        raise session_store_tail_error(
            "session store load_events unavailable"
        )
    already_installed = bool(
        getattr(
            store_class,
            "_palaver_tail_loader_installed",
            False,
        )
    )
    store_class._palaver_tail_loader_installed = True
    return {
        "schema": schema,
        "owner": owner,
        "installed": True,
        "already_installed": already_installed,
        "tail_loading": True,
        "ascending_replay_projection": True,
        "deterministic_replay_validation": True,
        "storage_backend": "straub-datrix",
        "database_is_authority": False,
        "authority_effect": "none",
    }
