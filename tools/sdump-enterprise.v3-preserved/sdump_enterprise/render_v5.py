from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from .model import Projection
from .palaver_context import (
    build_palaver_context,
)
from .palaver_render import (
    write_bundle as write_v4_bundle,
)
from .state_capsule import (
    build_state_capsule,
    stable_hash,
)


schema = "savant.sdump.render.v5.1"
border = "=" * 88


def _json(
    value: Any,
) -> str:
    try:
        import orjson

        return orjson.dumps(
            value,
            option=(
                orjson.OPT_INDENT_2
                | orjson.OPT_SORT_KEYS
            ),
        ).decode(
            "utf-8"
        )

    except ImportError:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )


def _sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def _write_section(
    handle: Any,
    name: str,
    value: Any,
) -> None:
    handle.write(
        f"{border}\n"
        f"{name}\n"
        f"{border}\n"
    )

    handle.write(
        _json(
            value
        )
    )

    handle.write(
        "\n"
    )


def write_bundle(
    output: Path,
    manifest: Mapping[str, Any],
    projection: Projection,
    pretty_manifest: bool = False,
) -> None:
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix="sdump-v5-render-",
        dir=str(
            output.parent
        ),
    ) as temporary_directory:
        temporary_root = Path(
            temporary_directory
        )

        compatibility = (
            temporary_root
            / "compatibility.txt"
        )

        write_v4_bundle(
            compatibility,
            manifest,
            projection,
            pretty_manifest=(
                pretty_manifest
            ),
        )

        compatibility_sha256 = (
            _sha256_file(
                compatibility
            )
        )

        compatibility_size = (
            compatibility
            .stat()
            .st_size
        )

        capsule = (
            build_state_capsule(
                manifest,
                projection,
            )
        )

        palaver_context = (
            build_palaver_context(
                manifest,
                projection,
            )
        )

        descriptor, temporary_name = (
            tempfile.mkstemp(
                prefix=(
                    f".{output.name}."
                ),
                suffix=".partial",
                dir=str(
                    output.parent
                ),
            )
        )

        temporary = Path(
            temporary_name
        )

        try:
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
                newline="",
            ) as handle:
                with compatibility.open(
                    "r",
                    encoding="utf-8",
                    errors="strict",
                    newline="",
                ) as source:
                    first = True

                    for line in source:
                        if first:
                            handle.write(
                                "sdump enterprise v5.1\n"
                            )

                            first = False
                            continue

                        handle.write(
                            line
                        )

                _write_section(
                    handle,
                    (
                        "15 v5 living "
                        "server state capsule"
                    ),
                    capsule,
                )

                capability_map = {
                    "schema":
                        schema,
                    "generation":
                        "5.1",
                    "projection_only":
                        True,
                    "authority_effect":
                        "none",
                    "compatibility_payload":
                        (
                            "v4 source transport "
                            "retained without "
                            "source-body mutation"
                        ),
                    "compatibility_source_sha256":
                        compatibility_sha256,
                    "compatibility_source_bytes":
                        compatibility_size,
                    "compatibility_header_upgraded":
                        True,
                    "source_line_indexes_preserved":
                        True,
                    "state_capsule_sha256":
                        capsule.get(
                            "capsule_sha256"
                        ),
                    "features":
                        {
                            "complete_deduplicated_source":
                                True,
                            "same_scope_tree":
                                True,
                            "explicit_source_completeness_receipt":
                                True,
                            "live_service_state":
                                True,
                            "deployment_state":
                                True,
                            "safe_environment_presence":
                                True,
                            "process_state_without_arguments":
                                True,
                            "listener_state":
                                True,
                            "nginx_state":
                                True,
                            "sqlite_metadata":
                                True,
                            "dependency_lock_state":
                                True,
                            "oversized_file_metadata":
                                True,
                            "filesystem_metadata_merkle_root":
                                True,
                            "projection_record_merkle_root":
                                True,
                            "living_state_bridge":
                                True,
                            "toolchain_versions":
                                True,
                            "host_resources":
                                True,
                            "secret_values_serialized":
                                False,
                        },
                }

                _write_section(
                    handle,
                    "16 v5 capability map",
                    capability_map,
                )

                compatibility_receipt = {
                    "schema":
                        (
                            "savant.sdump."
                            "v5.compatibility-receipt"
                        ),
                    "projection_only":
                        True,
                    "authority_effect":
                        "none",
                    "snapshot_sha256":
                        projection.snapshot_hash,
                    "manifest_sha256":
                        stable_hash(
                            manifest
                        ),
                    "compatibility_source_sha256":
                        compatibility_sha256,
                    "state_capsule_sha256":
                        capsule.get(
                            "capsule_sha256"
                        ),
                    "included_source_transport_generated":
                        True,
                    "state_capsule_generated":
                        True,
                    "external_runtime_probes":
                        "best-effort evidence",
                    "secret_values_serialized":
                        False,
                }

                _write_section(
                    handle,
                    (
                        "17 v5 compatibility "
                        "integrity receipt"
                    ),
                    compatibility_receipt,
                )

                _write_section(
                    handle,
                    (
                        "18 palaver portable "
                        "context"
                    ),
                    palaver_context,
                )

                _write_section(
                    handle,
                    (
                        "19 sanitized deployment "
                        "configuration"
                    ),
                    palaver_context.get(
                        "deployment_configuration"
                    ),
                )

                _write_section(
                    handle,
                    (
                        "20 bounded service "
                        "diagnostics"
                    ),
                    palaver_context.get(
                        "service_diagnostics"
                    ),
                )

                _write_section(
                    handle,
                    (
                        "21 portable living "
                        "state and delta"
                    ),
                    {
                        "living_state":
                            palaver_context.get(
                                "living_state"
                            ),
                        "delta":
                            palaver_context.get(
                                "delta"
                            ),
                    },
                )

                _write_section(
                    handle,
                    (
                        "22 sqlite semantic "
                        "state"
                    ),
                    palaver_context.get(
                        "sqlite_semantic_state"
                    ),
                )

                _write_section(
                    handle,
                    (
                        "23 complete hashes for "
                        "oversized objects"
                    ),
                    palaver_context.get(
                        "large_objects"
                    ),
                )

                _write_section(
                    handle,
                    (
                        "24 deterministic health "
                        "synthesis"
                    ),
                    palaver_context.get(
                        "health"
                    ),
                )

                final_receipt = {
                    "schema":
                        (
                            "savant.sdump."
                            "v5.1.integrity-receipt"
                        ),
                    "projection_only":
                        True,
                    "authority_effect":
                        "none",
                    "snapshot_sha256":
                        projection.snapshot_hash,
                    "manifest_sha256":
                        stable_hash(
                            manifest
                        ),
                    "compatibility_source_sha256":
                        compatibility_sha256,
                    "state_capsule_sha256":
                        capsule.get(
                            "capsule_sha256"
                        ),
                    "palaver_context_sha256":
                        palaver_context.get(
                            "context_sha256"
                        ),
                    "included_source_transport_generated":
                        True,
                    "state_capsule_generated":
                        True,
                    "palaver_context_generated":
                        True,
                    "sanitized_deployment_configuration_generated":
                        True,
                    "service_diagnostics_generated":
                        True,
                    "portable_living_state_generated":
                        True,
                    "sqlite_semantic_state_generated":
                        True,
                    "large_object_full_hashes_generated":
                        True,
                    "health_synthesis_generated":
                        True,
                    "secret_values_serialized":
                        False,
                    "terminal_marker":
                        (
                            "end sdump "
                            "enterprise v5.1 complete"
                        ),
                    "artifact_sha256_semantics":
                        (
                            "calculated by existing "
                            "cli after atomic render "
                            "completion"
                        ),
                }

                _write_section(
                    handle,
                    "25 v5.1 final integrity receipt",
                    final_receipt,
                )

                handle.write(
                    f"{border}\n"
                    "end sdump enterprise "
                    "v5.1 complete\n"
                    f"snapshot_sha256 "
                    f"{projection.snapshot_hash}\n"
                    "state_capsule_sha256 "
                    f"{capsule.get('capsule_sha256')}\n"
                    "palaver_context_sha256 "
                    f"{palaver_context.get('context_sha256')}\n"
                    "projection_only true\n"
                    "authority_effect none\n"
                    "secret_values_serialized false\n"
                    f"{border}\n"
                )

                handle.flush()

                os.fsync(
                    handle.fileno()
                )

            os.chmod(
                temporary,
                0o600,
            )

            os.replace(
                temporary,
                output,
            )

            directory_fd = os.open(
                output.parent,
                os.O_DIRECTORY,
            )

            try:
                os.fsync(
                    directory_fd
                )

            finally:
                os.close(
                    directory_fd
                )

        finally:
            if temporary.exists():
                temporary.unlink()
