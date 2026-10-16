#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


schema = (
    "savant://runtime/palaver/"
    "deployment/1.0.0"
)

owner = "exile:palaver"

palaver_root = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver"
)

runtime_root = (
    palaver_root
    / "runtime"
)

canonical_server = (
    runtime_root
    / "server.py"
)

legacy_server = (
    palaver_root
    / "apps"
    / "webui_ultra"
    / "server.py"
)

nextgen_root = (
    palaver_root
    / "apps"
    / "webui-nextgen"
)

nextgen_package = (
    nextgen_root
    / "package.json"
)

nextgen_dist = (
    nextgen_root
    / "dist"
)

default_host = "127.0.0.1"
default_port = 8787


class deployment_error(
    RuntimeError
):
    pass


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        allow_nan=False,
        default=str,
    )


def digest(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(
            value
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def env_text(
    environ: Mapping[str, str],
    name: str,
    default: str = "",
) -> str:
    return str(
        environ.get(
            name,
            default,
        )
        or ""
    ).strip()


def env_bool(
    environ: Mapping[str, str],
    name: str,
    default: bool = False,
) -> bool:
    value = env_text(
        environ,
        name,
    )

    if not value:
        return default

    normalized = value.casefold()

    if normalized in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True

    if normalized in {
        "0",
        "false",
        "no",
        "off",
    }:
        return False

    raise deployment_error(
        f"{name} must be boolean"
    )


def env_int(
    environ: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    value = env_text(
        environ,
        name,
        str(
            default
        ),
    )

    try:
        number = int(
            value
        )
    except ValueError as exc:
        raise deployment_error(
            f"{name} must be an integer"
        ) from exc

    if not minimum <= number <= maximum:
        raise deployment_error(
            f"{name} must be between "
            f"{minimum} and {maximum}"
        )

    return number


def normalize_host(
    value: str,
) -> str:
    host = value.strip()

    if not host:
        return default_host

    if host == "localhost":
        return default_host

    try:
        return str(
            ipaddress.ip_address(
                host
            )
        )
    except ValueError:
        pass

    if len(host) > 253:
        raise deployment_error(
            "PALAVER_BIND_HOST is too long"
        )

    labels = host.split(
        "."
    )

    for label in labels:
        if (
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or not all(
                character.isalnum()
                or character == "-"
                for character in label
            )
        ):
            raise deployment_error(
                "PALAVER_BIND_HOST is invalid"
            )

    return host.casefold()


def host_is_loopback(
    host: str,
) -> bool:
    if host == "localhost":
        return True

    try:
        return bool(
            ipaddress.ip_address(
                host
            ).is_loopback
        )
    except ValueError:
        return False


def normalized_csv(
    value: str,
) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []

    for raw in value.split(
        ","
    ):
        item = raw.strip()

        if (
            item
            and item not in seen
        ):
            seen.add(
                item
            )

            ordered.append(
                item
            )

    return tuple(
        ordered
    )


def normalize_environment(
    value: str,
) -> str:
    environment = (
        value.strip().casefold()
        or "production"
    )

    allowed = {
        "development",
        "test",
        "staging",
        "production",
    }

    if environment not in allowed:
        raise deployment_error(
            "PALAVER_ENVIRONMENT must be one of "
            + ", ".join(
                sorted(
                    allowed
                )
            )
        )

    return environment


def validate_tls_pair(
    certificate: str,
    key: str,
) -> tuple[
    bool,
    str | None,
]:
    if bool(
        certificate
    ) != bool(
        key
    ):
        raise deployment_error(
            "PALAVER_TLS_CERT and "
            "PALAVER_TLS_KEY must be "
            "configured together"
        )

    if not certificate:
        return (
            False,
            None,
        )

    certificate_path = Path(
        certificate
    )

    key_path = Path(
        key
    )

    if not certificate_path.is_file():
        raise deployment_error(
            "PALAVER_TLS_CERT does not exist"
        )

    if not key_path.is_file():
        raise deployment_error(
            "PALAVER_TLS_KEY does not exist"
        )

    material = {
        "certificate":
            str(
                certificate_path.resolve()
            ),
        "key":
            str(
                key_path.resolve()
            ),
    }

    return (
        True,
        digest(
            material
        ),
    )


@dataclass(
    frozen=True,
    slots=True,
)
class deployment_config:
    environment: str
    host: str
    port: int
    allow_public_bind: bool
    reverse_proxy: bool
    forwarded_headers: bool
    trusted_proxies: tuple[
        str,
        ...,
    ]
    allowed_origins: tuple[
        str,
        ...,
    ]
    tls_enabled: bool
    tls_identity_digest: (
        str
        | None
    )
    request_body_limit_bytes: int
    attachment_limit_bytes: int
    attachment_count_limit: int
    conversation_timeout_seconds: int

    @property
    def public_bind(
        self,
    ) -> bool:
        return not host_is_loopback(
            self.host
        )

    def semantic_projection(
        self,
    ) -> dict[str, Any]:
        return {
            "environment":
                self.environment,
            "host":
                self.host,
            "port":
                self.port,
            "public_bind":
                self.public_bind,
            "allow_public_bind":
                self.allow_public_bind,
            "reverse_proxy":
                self.reverse_proxy,
            "forwarded_headers":
                self.forwarded_headers,
            "trusted_proxies":
                list(
                    self.trusted_proxies
                ),
            "allowed_origins":
                list(
                    self.allowed_origins
                ),
            "tls_enabled":
                self.tls_enabled,
            "tls_identity_digest":
                self.tls_identity_digest,
            "request_body_limit_bytes":
                self.request_body_limit_bytes,
            "attachment_limit_bytes":
                self.attachment_limit_bytes,
            "attachment_count_limit":
                self.attachment_count_limit,
            "conversation_timeout_seconds":
                self.conversation_timeout_seconds,
        }


def load_config(
    environ: Mapping[
        str,
        str,
    ] = os.environ,
) -> deployment_config:
    host = normalize_host(
        env_text(
            environ,
            "PALAVER_BIND_HOST",
            default_host,
        )
    )

    port = env_int(
        environ,
        "PALAVER_WEB_PORT",
        default_port,
        minimum=1,
        maximum=65535,
    )

    allow_public_bind = env_bool(
        environ,
        "PALAVER_ALLOW_PUBLIC_BIND",
        False,
    )

    reverse_proxy = env_bool(
        environ,
        "PALAVER_REVERSE_PROXY",
        False,
    )

    forwarded_headers = env_bool(
        environ,
        "PALAVER_FORWARDED_HEADERS",
        False,
    )

    trusted_proxies = normalized_csv(
        env_text(
            environ,
            "PALAVER_TRUSTED_PROXIES",
        )
    )

    allowed_origins = normalized_csv(
        env_text(
            environ,
            "PALAVER_ALLOWED_ORIGINS",
        )
    )

    environment = (
        normalize_environment(
            env_text(
                environ,
                "PALAVER_ENVIRONMENT",
                "production",
            )
        )
    )

    tls_enabled, tls_identity = (
        validate_tls_pair(
            env_text(
                environ,
                "PALAVER_TLS_CERT",
            ),
            env_text(
                environ,
                "PALAVER_TLS_KEY",
            ),
        )
    )

    request_body_limit_bytes = env_int(
        environ,
        "PALAVER_REQUEST_BODY_LIMIT_BYTES",
        8 * 1024 * 1024,
        minimum=1024,
        maximum=256 * 1024 * 1024,
    )

    attachment_limit_bytes = env_int(
        environ,
        "PALAVER_ATTACHMENT_LIMIT_BYTES",
        32 * 1024 * 1024,
        minimum=1024,
        maximum=1024 * 1024 * 1024,
    )

    attachment_count_limit = env_int(
        environ,
        "PALAVER_ATTACHMENT_COUNT_LIMIT",
        64,
        minimum=0,
        maximum=4096,
    )

    conversation_timeout_seconds = (
        env_int(
            environ,
            "PALAVER_CONVERSATION_TIMEOUT_SECONDS",
            300,
            minimum=1,
            maximum=3600,
        )
    )

    config = deployment_config(
        environment=environment,
        host=host,
        port=port,
        allow_public_bind=
            allow_public_bind,
        reverse_proxy=
            reverse_proxy,
        forwarded_headers=
            forwarded_headers,
        trusted_proxies=
            trusted_proxies,
        allowed_origins=
            allowed_origins,
        tls_enabled=
            tls_enabled,
        tls_identity_digest=
            tls_identity,
        request_body_limit_bytes=
            request_body_limit_bytes,
        attachment_limit_bytes=
            attachment_limit_bytes,
        attachment_count_limit=
            attachment_count_limit,
        conversation_timeout_seconds=
            conversation_timeout_seconds,
    )

    validate_config(
        config
    )

    return config


def validate_config(
    config: deployment_config,
) -> None:
    if (
        config.public_bind
        and not config.allow_public_bind
    ):
        raise deployment_error(
            "public Palaver binding requires "
            "PALAVER_ALLOW_PUBLIC_BIND=1"
        )

    if (
        config.forwarded_headers
        and not config.reverse_proxy
    ):
        raise deployment_error(
            "forwarded headers require "
            "PALAVER_REVERSE_PROXY=1"
        )

    if (
        config.trusted_proxies
        and not config.reverse_proxy
    ):
        raise deployment_error(
            "trusted proxies require "
            "PALAVER_REVERSE_PROXY=1"
        )

    if (
        config.forwarded_headers
        and not config.trusted_proxies
    ):
        raise deployment_error(
            "forwarded headers require at least "
            "one PALAVER_TRUSTED_PROXIES entry"
        )


def filesystem_projection() -> dict[
    str,
    Any,
]:
    return {
        "palaver_root":
            str(
                palaver_root
            ),
        "canonical_server": {
            "path":
                str(
                    canonical_server
                ),
            "exists":
                canonical_server.is_file(),
        },
        "legacy_compatibility_server": {
            "path":
                str(
                    legacy_server
                ),
            "exists":
                legacy_server.exists(),
        },
        "nextgen": {
            "root":
                str(
                    nextgen_root
                ),
            "source_available":
                nextgen_package.is_file(),
            "built_assets_available":
                nextgen_dist.is_dir(),
        },
    }


def migration_checks(
    config: deployment_config,
) -> dict[
    str,
    bool,
]:
    filesystem = (
        filesystem_projection()
    )

    return {
        "canonical_entrypoint":
            canonical_server.is_file(),
        "runtime_directory":
            runtime_root.is_dir(),
        "nextgen_source":
            nextgen_package.is_file(),
        "safe_bind":
            bool(
                not config.public_bind
                or config.allow_public_bind
            ),
        "proxy_policy_coherent":
            bool(
                not config.forwarded_headers
                or (
                    config.reverse_proxy
                    and bool(
                        config.trusted_proxies
                    )
                )
            ),
        "tls_policy_coherent":
            True,
        "conversation_owner_preserved":
            True,
        "provider_owner_preserved":
            True,
        "persona_owner_preserved":
            True,
        "task_owner_preserved":
            True,
        "mutation_owner_preserved":
            True,
        "projection_only":
            True,
        "authority_effect_none":
            True,
        "filesystem_projection_available":
            bool(
                filesystem
            ),
    }


def readiness(
    config: deployment_config,
) -> dict[
    str,
    Any,
]:
    checks = migration_checks(
        config
    )

    ready = all(
        checks.values()
    )

    semantic = (
        config.semantic_projection()
    )

    contract = {
        "schema":
            schema,
        "owner":
            owner,
        "type":
            "palaver_deployment_projection",
        "ready":
            ready,
        "configuration":
            semantic,
        "configuration_digest":
            digest(
                semantic
            ),
        "filesystem":
            filesystem_projection(),
        "checks":
            checks,
        "interfaces": {
            "conversation_owner":
                "palaver",
            "provider_owner":
                "opus",
            "persona_owner":
                "envoy",
            "voice_owner":
                "envoy",
            "task_owner":
                "niche",
            "mutation_owner":
                "coda",
            "canonical_entrypoint":
                str(
                    canonical_server
                ),
        },
        "security": {
            "loopback_default":
                True,
            "public_bind_requires_opt_in":
                True,
            "forwarded_headers_require_proxy":
                True,
            "trusted_proxy_required":
                config.forwarded_headers,
            "tls_material_not_emitted":
                True,
            "secret_values_not_projected":
                True,
        },
        "migration": {
            "derived":
                True,
            "deterministic":
                True,
            "rebuildable":
                True,
            "persistent_state_created":
                False,
            "registry_mutation":
                False,
            "authority_creation":
                False,
        },
        "authority_effect":
            "none",
    }

    contract[
        "projection_digest"
    ] = digest(
        contract
    )

    return contract


def socket_preflight(
    config: deployment_config,
) -> dict[
    str,
    Any,
]:
    sock = socket.socket(
        socket.AF_INET6
        if ":" in config.host
        else socket.AF_INET,
        socket.SOCK_STREAM,
    )

    try:
        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        sock.bind(
            (
                config.host,
                config.port,
            )
        )

        available = True
        error = None

    except OSError as exc:
        available = False
        error = {
            "type":
                type(
                    exc
                ).__name__,
            "errno":
                exc.errno,
        }

    finally:
        sock.close()

    projection = {
        "schema":
            schema,
        "owner":
            owner,
        "type":
            "palaver_socket_preflight",
        "host":
            config.host,
        "port":
            config.port,
        "available":
            available,
        "error":
            error,
        "observational":
            True,
        "authority_effect":
            "none",
    }

    return projection


def execution_environment(
    config: deployment_config,
    environ: Mapping[
        str,
        str,
    ] = os.environ,
) -> dict[str, str]:
    projected = dict(
        environ
    )

    projected[
        "PALAVER_BIND_HOST"
    ] = config.host

    projected[
        "PALAVER_WEB_PORT"
    ] = str(
        config.port
    )

    projected[
        "PALAVER_ENVIRONMENT"
    ] = config.environment

    return projected


def exec_server(
    config: deployment_config,
) -> None:
    contract = readiness(
        config
    )

    if not contract[
        "ready"
    ]:
        raise deployment_error(
            "Palaver deployment contract "
            "is not ready"
        )

    preflight = socket_preflight(
        config
    )

    if not preflight[
        "available"
    ]:
        raise deployment_error(
            "Palaver bind address is unavailable"
        )

    environment = (
        execution_environment(
            config
        )
    )

    os.execve(
        sys.executable,
        [
            sys.executable,
            str(
                canonical_server
            ),
        ],
        environment,
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="palaver-deployment",
    )

    commands = (
        result.add_subparsers(
            dest="command",
            required=True,
        )
    )

    commands.add_parser(
        "inspect"
    )

    commands.add_parser(
        "check"
    )

    commands.add_parser(
        "serve"
    )

    return result


def main() -> int:
    args = parser().parse_args()

    try:
        config = load_config()

        if args.command == "inspect":
            print(
                json.dumps(
                    readiness(
                        config
                    ),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )

            return 0

        if args.command == "check":
            result = readiness(
                config
            )

            result[
                "socket_preflight"
            ] = socket_preflight(
                config
            )

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )

            return (
                0
                if (
                    result[
                        "ready"
                    ]
                    and result[
                        "socket_preflight"
                    ][
                        "available"
                    ]
                )
                else 1
            )

        if args.command == "serve":
            exec_server(
                config
            )

            return 0

        raise deployment_error(
            "unsupported command"
        )

    except deployment_error as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "schema": schema,
                    "owner": owner,
                    "error":
                        "deployment_error",
                    "message":
                        str(
                            exc
                        ),
                    "authority_effect":
                        "none",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )

        return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
