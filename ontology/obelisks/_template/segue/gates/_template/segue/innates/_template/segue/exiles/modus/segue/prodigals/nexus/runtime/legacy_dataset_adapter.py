#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"

SECTION_KIND = {
    "events": "event",
    "evidence": "evidence",
    "emails": "communication",
    "transcript": "transcript",
    "legal": "authority",
    "assets": "asset",
    "claims": "claim",
    "corpus": "corpus-record",
    "relations": "relation",
    "project_sources": "source-reference",
    "entities": "entity",
    "case_metadata": "matter-metadata",
    "matter_metadata": "matter-metadata",
    "work_ledger": "work-record",
    "exhibit_a_metadata": "media-metadata",
    "litigation_work_product": "work-product"
}

PRESENTATION_STATE = {
    "corroborated": "gold",
    "reported": "pink",
    "inferred": "pink",
    "disputed": "gray",
    "unknown": "gray"
}


class NexusLegacyDatasetError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_object(value: Any) -> str:
    return sha256_text(canonical_json(value))


def slug(value: str) -> str:
    result = re.sub(
        r"[^a-z0-9]+",
        "-",
        value.lower()
    ).strip("-")

    return result or "record"


def evidentiary_state_candidate(
    payload: Any
) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return (
            "unknown",
            "non-object legacy payload"
        )

    raw = str(
        payload.get("status", "")
    ).strip().lower()

    if not raw:
        return (
            "unknown",
            "legacy record carries no explicit status"
        )

    if any(
        token in raw
        for token in (
            "unknown",
            "pending",
            "not obtained",
            "not yet obtained",
            "missing",
            "unclear",
            "unverified",
            "not verified"
        )
    ):
        return (
            "unknown",
            "legacy status explicitly expresses uncertainty"
        )

    if any(
        token in raw
        for token in (
            "disputed",
            "contradiction",
            "conflict",
            "contested"
        )
    ):
        return (
            "disputed",
            "legacy status explicitly expresses dispute"
        )

    if any(
        token in raw
        for token in (
            "user-reported",
            "user reported",
            "reported",
            "alleged",
            "allegation",
            "witness-reported",
            "witness reported"
        )
    ):
        return (
            "reported",
            "legacy status identifies reported or alleged material"
        )

    if any(
        token in raw
        for token in (
            "inference",
            "inferred",
            "interpretive",
            "speculative",
            "speculation"
        )
    ):
        return (
            "inferred",
            "legacy status identifies inference or interpretation"
        )

    if any(
        token in raw
        for token in (
            "primary government document",
            "primary document",
            "documentary",
            "proof label",
            "proof-labeled",
            "gmail proof",
            "government record",
            "official record",
            "verified transcript",
            "verified source"
        )
    ):
        return (
            "corroborated",
            "legacy status identifies direct documentary support"
        )

    return (
        "unknown",
        "legacy status preserved without semantic promotion"
    )


@dataclass(frozen=True, slots=True)
class NormalizedRecord:
    id: str
    section: str
    index: int | None
    semantic_kind: str
    epistemic_layer: str
    external_id: Any
    legacy_status: Any
    evidentiary_state_candidate: str
    evidentiary_state_basis: str
    payload_sha256: str
    payload: Any

    def projection(self) -> dict[str, Any]:
        return {
            "schema": (
                "savant://nexus/legacy-normalized-record/"
                + SCHEMA_VERSION
            ),
            "id": self.id,
            "kind": self.semantic_kind,
            "source_section": self.section,
            "source_index": self.index,
            "external_id": self.external_id,
            "epistemic_layer": self.epistemic_layer,
            "legacy_status": self.legacy_status,
            "evidentiary_state_candidate": (
                self.evidentiary_state_candidate
            ),
            "presentation_state_candidate": (
                PRESENTATION_STATE[
                    self.evidentiary_state_candidate
                ]
            ),
            "evidentiary_state_basis": (
                self.evidentiary_state_basis
            ),
            "authority": {
                "state": "none",
                "effect": "none"
            },
            "payload_sha256": self.payload_sha256,
            "payload": self.payload
        }


class LegacyDatasetAdapter:
    schema = (
        "savant://nexus/legacy-dataset-adapter/"
        + SCHEMA_VERSION
    )

    def __init__(self, source: str | Path):
        self.source = Path(source).resolve()

        if not self.source.is_file():
            raise NexusLegacyDatasetError(
                "source file does not exist: "
                + str(self.source)
            )

        self.source_bytes = self.source.read_bytes()

        try:
            self.source_text = (
                self.source_bytes.decode("utf-8")
            )
        except UnicodeDecodeError:
            self.source_text = (
                self.source_bytes.decode(
                    "utf-8",
                    errors="replace"
                )
            )

        self.source_sha256 = sha256_bytes(
            self.source_bytes
        )

        self.data = self._extract_data()

        if not isinstance(self.data, dict):
            raise NexusLegacyDatasetError(
                "legacy DATA root must be an object"
            )

        self.data_sha256 = sha256_object(self.data)

        self.records = self._normalize()

        reconstructed = self.reconstruct()

        self.reconstructed_sha256 = (
            sha256_object(reconstructed)
        )

        if reconstructed != self.data:
            raise NexusLegacyDatasetError(
                "lossless reconstruction check failed"
            )

        if (
            self.reconstructed_sha256
            != self.data_sha256
        ):
            raise NexusLegacyDatasetError(
                "reconstruction digest mismatch"
            )

    def _extract_data(self) -> dict[str, Any]:
        marker = "const DATA="

        offset = self.source_text.find(marker)

        if offset < 0:
            marker = "const DATA ="
            offset = self.source_text.find(marker)

        if offset < 0:
            raise NexusLegacyDatasetError(
                "legacy source contains no const DATA assignment"
            )

        payload_start = offset + len(marker)

        candidate = self.source_text[
            payload_start:
        ].lstrip()

        decoder = json.JSONDecoder()

        try:
            value, _ = decoder.raw_decode(
                candidate
            )
        except json.JSONDecodeError as exc:
            raise NexusLegacyDatasetError(
                "legacy DATA is not strict JSON: "
                + str(exc)
            ) from exc

        if not isinstance(value, dict):
            raise NexusLegacyDatasetError(
                "legacy DATA assignment is not an object"
            )

        return value

    def _record_id(
        self,
        *,
        section: str,
        index: int | None,
        payload: Any
    ) -> str:
        material = {
            "source_sha256": self.source_sha256,
            "section": section,
            "index": index,
            "payload_sha256": sha256_object(payload)
        }

        identity = sha256_object(material)[:24]

        position = (
            "singleton"
            if index is None
            else f"{index:06d}"
        )

        return (
            "nexus.import."
            + slug(section)
            + "."
            + position
            + "."
            + identity
        )

    def _epistemic_layer(
        self,
        section: str
    ) -> str:
        if section == "project_sources":
            return "original-source"

        return "normalized-record"

    def _normalize_payload(
        self,
        *,
        section: str,
        index: int | None,
        payload: Any
    ) -> NormalizedRecord:
        external_id = None
        legacy_status = None

        if isinstance(payload, dict):
            external_id = payload.get("id")
            legacy_status = payload.get(
                "status"
            )

        state, basis = (
            evidentiary_state_candidate(
                payload
            )
        )

        return NormalizedRecord(
            id=self._record_id(
                section=section,
                index=index,
                payload=payload
            ),
            section=section,
            index=index,
            semantic_kind=SECTION_KIND.get(
                section,
                "legacy-record"
            ),
            epistemic_layer=(
                self._epistemic_layer(section)
            ),
            external_id=external_id,
            legacy_status=legacy_status,
            evidentiary_state_candidate=state,
            evidentiary_state_basis=basis,
            payload_sha256=sha256_object(
                payload
            ),
            payload=payload
        )

    def _normalize(
        self
    ) -> tuple[NormalizedRecord, ...]:
        records: list[NormalizedRecord] = []

        for section, value in self.data.items():
            if isinstance(value, list):
                for index, payload in enumerate(
                    value
                ):
                    records.append(
                        self._normalize_payload(
                            section=section,
                            index=index,
                            payload=payload
                        )
                    )
            else:
                records.append(
                    self._normalize_payload(
                        section=section,
                        index=None,
                        payload=value
                    )
                )

        return tuple(records)

    def reconstruct(self) -> dict[str, Any]:
        rebuilt: dict[str, Any] = {}

        by_section: dict[
            str,
            list[NormalizedRecord]
        ] = {}

        for record in self.records:
            by_section.setdefault(
                record.section,
                []
            ).append(record)

        for section in self.data.keys():
            original = self.data[section]
            records = by_section[section]

            if isinstance(original, list):
                ordered = sorted(
                    records,
                    key=lambda item: (
                        -1
                        if item.index is None
                        else item.index
                    )
                )

                rebuilt[section] = [
                    item.payload
                    for item in ordered
                ]
            else:
                if len(records) != 1:
                    raise NexusLegacyDatasetError(
                        "singleton section changed cardinality: "
                        + section
                    )

                rebuilt[section] = (
                    records[0].payload
                )

        return rebuilt

    def section_counts(self) -> dict[str, int]:
        result: dict[str, int] = {}

        for section, value in self.data.items():
            result[section] = (
                len(value)
                if isinstance(value, list)
                else 1
            )

        return result

    def state_counts(self) -> dict[str, int]:
        counts = Counter(
            record.evidentiary_state_candidate
            for record in self.records
        )

        return {
            key: counts.get(key, 0)
            for key in PRESENTATION_STATE
        }

    def projection(self) -> dict[str, Any]:
        payload = {
            "schema": self.schema,
            "kind": "nexus-legacy-dataset-projection",
            "status": "candidate",
            "authoritative": False,
            "authority_effect": "none",
            "mutation_authorized": False,
            "rebuildable": True,
            "lossless": True,
            "source": {
                "path": str(self.source),
                "sha256": self.source_sha256,
                "data_sha256": self.data_sha256
            },
            "top_level_order": list(
                self.data.keys()
            ),
            "section_counts": (
                self.section_counts()
            ),
            "record_count": len(
                self.records
            ),
            "state_candidate_counts": (
                self.state_counts()
            ),
            "records": [
                record.projection()
                for record in self.records
            ],
            "reconstruction": {
                "valid": True,
                "sha256": (
                    self.reconstructed_sha256
                ),
                "matches_source_data": (
                    self.reconstructed_sha256
                    == self.data_sha256
                )
            },
            "epistemic_contract": {
                "source_is_not_fact": True,
                "normalization_is_not_admission": True,
                "state_candidates_are_not_authority": True,
                "presentation_color_is_derived": True,
                "ai_authority_effect": "none"
            },
            "provenance": {
                "adapter": (
                    "prodigal:nexus/"
                    "runtime/legacy_dataset_adapter.py"
                ),
                "source_format": (
                    "legacy nexus html embedded const DATA"
                ),
                "transformation": (
                    "lossless structural normalization"
                )
            }
        }

        payload["projection_sha256"] = (
            sha256_object(payload)
        )

        return payload

    def receipt(self) -> dict[str, Any]:
        projection = self.projection()

        return {
            "schema": (
                "savant://nexus/import-receipt/"
                + SCHEMA_VERSION
            ),
            "kind": "migration-receipt",
            "status": "candidate",
            "authoritative": False,
            "authority_effect": "none",
            "mutation_authorized": False,
            "source_path": str(self.source),
            "source_sha256": (
                self.source_sha256
            ),
            "source_data_sha256": (
                self.data_sha256
            ),
            "projection_sha256": (
                projection[
                    "projection_sha256"
                ]
            ),
            "reconstructed_data_sha256": (
                self.reconstructed_sha256
            ),
            "lossless_reconstruction": True,
            "section_counts": (
                self.section_counts()
            ),
            "record_count": len(
                self.records
            ),
            "state_candidate_counts": (
                self.state_counts()
            ),
            "semantic_changes": 0,
            "dropped_sections": [],
            "dropped_records": [],
            "authority_changes": 0,
            "notes": [
                "legacy payloads are preserved verbatim as parsed JSON values",
                "external identifiers retain original spelling and case",
                "internal nexus import identifiers are lowercase",
                "evidentiary states are candidates only and have no authority effect",
                "legacy presentation metadata remains inside preserved payloads",
                "no canon or accepted authority is mutated by this adapter"
            ]
        }


def load_legacy_dataset(
    source: str | Path
) -> LegacyDatasetAdapter:
    return LegacyDatasetAdapter(source)
