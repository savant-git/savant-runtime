from __future__ import annotations

from typing import Any

try:
    from .response_policy import (
        sanitize_public_payload,
    )
except ImportError:
    from response_policy import (
        sanitize_public_payload,
    )


schema = (
    "savant://runtime/palaver/"
    "response-integration/1.0.0"
)

owner = "exile:palaver"


class response_integration_error(
    RuntimeError
):
    pass


def install(
    server_module: Any,
) -> dict[str, Any]:
    if getattr(
        server_module,
        "_palaver_response_policy_installed",
        False,
    ):
        return {
            "schema": schema,
            "owner": owner,
            "installed": True,
            "already_installed": True,
            "authority_effect": "none",
        }

    original_factory = getattr(
        server_module,
        "make_canonical_handler",
        None,
    )

    if not callable(
        original_factory
    ):
        raise response_integration_error(
            "canonical handler factory unavailable"
        )

    def response_policy_factory(
        legacy: Any,
    ):
        base_handler = (
            original_factory(
                legacy
            )
        )

        class response_policy_handler(
            base_handler
        ):
            def send_json(
                self,
                payload: Any,
                status: int = 200,
                *args: Any,
                **kwargs: Any,
            ) -> Any:
                sanitized = (
                    sanitize_public_payload(
                        payload
                    )
                )

                return super().send_json(
                    sanitized,
                    status,
                    *args,
                    **kwargs,
                )

        response_policy_handler.__name__ = (
            "palaver_response_policy_handler"
        )

        return response_policy_handler

    server_module.make_canonical_handler = (
        response_policy_factory
    )

    server_module._palaver_response_policy_installed = (
        True
    )

    return {
        "schema": schema,
        "owner": owner,
        "installed": True,
        "already_installed": False,
        "public_diagnostics":
            False,
        "internal_exceptions_modified":
            False,
        "canonical_handler_modified":
            False,
        "authority_effect":
            "none",
    }
