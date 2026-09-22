from __future__ import annotations

from typing import Any

try:
    from .sequence_recovery import (
        restore_bounded_history,
    )
    from .session_store import (
        session_store,
    )
    from .session_store_tail import (
        install as install_tail_loader,
    )
    import session_runtime as session_runtime_module
except ImportError:
    from sequence_recovery import (
        restore_bounded_history,
    )
    from session_store import (
        session_store,
    )
    from session_store_tail import (
        install as install_tail_loader,
    )
    import session_runtime as session_runtime_module


schema = (
    "savant://runtime/palaver/"
    "session-recovery-integration/1.0.0"
)

owner = "exile:palaver"


class session_recovery_integration_error(
    RuntimeError
):
    pass


def install() -> dict[str, Any]:
    tail = install_tail_loader(
        session_store
    )

    runtime_class = getattr(
        session_runtime_module,
        "session_runtime",
        None,
    )

    if runtime_class is None:
        raise session_recovery_integration_error(
            "session runtime class unavailable"
        )

    if getattr(
        runtime_class,
        "_palaver_bounded_recovery_installed",
        False,
    ):
        return {
            "schema": schema,
            "owner": owner,
            "installed": True,
            "already_installed": True,
            "tail_loader": tail,
            "authority_effect": "none",
        }

    original_buffer = getattr(
        runtime_class,
        "_buffer",
        None,
    )

    if not callable(
        original_buffer
    ):
        raise session_recovery_integration_error(
            "session runtime buffer resolver unavailable"
        )

    def _buffer(
        self: Any,
        session: str,
    ):
        identifier = str(
            session
            or ""
        ).strip()

        registry = getattr(
            self,
            "registry",
            None,
        )

        if registry is None:
            registry = getattr(
                self,
                "transport",
                None,
            )

        if registry is None:
            return original_buffer(
                self,
                identifier,
            )

        restored = getattr(
            self,
            "_restored",
            None,
        )

        if restored is None:
            restored = getattr(
                self,
                "_restored_sessions",
                None,
            )

        if (
            isinstance(
                restored,
                set,
            )
            and identifier
            in restored
        ):
            return original_buffer(
                self,
                identifier,
            )

        getter = getattr(
            registry,
            "get",
            None,
        )

        if not callable(
            getter
        ):
            getter = getattr(
                registry,
                "open",
                None,
            )

        if not callable(
            getter
        ):
            return original_buffer(
                self,
                identifier,
            )

        try:
            buffer = getter(
                identifier
            )
        except TypeError:
            return original_buffer(
                self,
                identifier,
            )

        store = getattr(
            self,
            "store",
            None,
        )

        if store is None:
            return original_buffer(
                self,
                identifier,
            )

        capacity = int(
            getattr(
                self,
                "maximum_events_per_session",
                1024,
            )
            or 1024
        )

        restore_bounded_history(
            store=store,
            buffer=buffer,
            session=identifier,
            capacity=capacity,
        )

        if isinstance(
            restored,
            set,
        ):
            restored.add(
                identifier
            )

        return buffer

    runtime_class._buffer = (
        _buffer
    )

    runtime_class._palaver_bounded_recovery_installed = (
        True
    )

    return {
        "schema": schema,
        "owner": owner,
        "installed": True,
        "already_installed": False,
        "tail_loader": tail,
        "bounded_retention":
            True,
        "persistent_sequence_continuity":
            True,
        "restart_sequence_reset":
            False,
        "database_is_authority":
            False,
        "authority_effect":
            "none",
    }
