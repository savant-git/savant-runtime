from __future__ import annotations

from .deployment import (
    default_host,
    deployment_error,
    digest,
    load_config,
    readiness,
)


def main() -> int:
    base = {
        "PALAVER_ENVIRONMENT":
            "production",
        "PALAVER_BIND_HOST":
            "127.0.0.1",
        "PALAVER_WEB_PORT":
            "8787",
        "PALAVER_REQUEST_BODY_LIMIT_BYTES":
            "8388608",
        "PALAVER_ATTACHMENT_LIMIT_BYTES":
            "33554432",
        "PALAVER_ATTACHMENT_COUNT_LIMIT":
            "64",
        "PALAVER_CONVERSATION_TIMEOUT_SECONDS":
            "300",
    }

    first = load_config(
        base
    )

    second = load_config(
        dict(
            reversed(
                list(
                    base.items()
                )
            )
        )
    )

    assert first.host == default_host
    assert first.port == 8787
    assert first.public_bind is False

    assert (
        first.semantic_projection()
        == second.semantic_projection()
    )

    assert (
        digest(
            first.semantic_projection()
        )
        == digest(
            second.semantic_projection()
        )
    )

    projection = readiness(
        first
    )

    assert (
        projection[
            "authority_effect"
        ]
        == "none"
    )

    assert (
        projection[
            "migration"
        ][
            "persistent_state_created"
        ]
        is False
    )

    assert (
        projection[
            "interfaces"
        ][
            "conversation_owner"
        ]
        == "palaver"
    )

    assert (
        projection[
            "interfaces"
        ][
            "provider_owner"
        ]
        == "opus"
    )

    assert (
        projection[
            "interfaces"
        ][
            "persona_owner"
        ]
        == "envoy"
    )

    assert (
        projection[
            "interfaces"
        ][
            "task_owner"
        ]
        == "niche"
    )

    assert (
        projection[
            "interfaces"
        ][
            "mutation_owner"
        ]
        == "coda"
    )

    public_rejected = False

    try:
        load_config(
            {
                **base,
                "PALAVER_BIND_HOST":
                    "0.0.0.0",
            }
        )
    except deployment_error:
        public_rejected = True

    assert public_rejected

    public_allowed = load_config(
        {
            **base,
            "PALAVER_BIND_HOST":
                "0.0.0.0",
            "PALAVER_ALLOW_PUBLIC_BIND":
                "1",
        }
    )

    assert (
        public_allowed.public_bind
        is True
    )

    assert (
        public_allowed.allow_public_bind
        is True
    )

    forwarded_rejected = False

    try:
        load_config(
            {
                **base,
                "PALAVER_FORWARDED_HEADERS":
                    "1",
            }
        )
    except deployment_error:
        forwarded_rejected = True

    assert forwarded_rejected

    proxy = load_config(
        {
            **base,
            "PALAVER_REVERSE_PROXY":
                "1",
            "PALAVER_FORWARDED_HEADERS":
                "1",
            "PALAVER_TRUSTED_PROXIES":
                "127.0.0.1,10.0.0.1",
        }
    )

    assert (
        proxy.reverse_proxy
        is True
    )

    assert (
        proxy.forwarded_headers
        is True
    )

    assert proxy.trusted_proxies == (
        "127.0.0.1",
        "10.0.0.1",
    )

    invalid_port_rejected = False

    try:
        load_config(
            {
                **base,
                "PALAVER_WEB_PORT":
                    "70000",
            }
        )
    except deployment_error:
        invalid_port_rejected = True

    assert invalid_port_rejected

    print(
        "palaver deployment: ok"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
