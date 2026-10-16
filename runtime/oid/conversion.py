from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Any, Mapping

from runtime.oid.clock import ClockEstimate
from runtime.oid.core import TemporalInterval


SCHEMA = "savant://oid/conversion/1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError(
            "oid conversion requires timezone information"
        )

    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return (
        _utc(value)
        .isoformat()
        .replace("+00:00", "Z")
    )


@dataclass(frozen=True, slots=True)
class ConvertedTimestamp:
    source_clock_ref: str
    original_timestamp: str
    normalized_utc: datetime
    projected_utc: datetime
    clock_offset_seconds: float
    uncertainty_seconds: float
    correction_applied: bool

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "source_clock_ref": (
                self.source_clock_ref
            ),
            "original_timestamp": (
                self.original_timestamp
            ),
            "normalized_utc": _iso(
                self.normalized_utc
            ),
            "projected_utc": _iso(
                self.projected_utc
            ),
            "clock_offset_seconds": float(
                self.clock_offset_seconds
            ),
            "uncertainty_seconds": float(
                self.uncertainty_seconds
            ),
            "correction_applied": (
                self.correction_applied
            ),
            "original_timestamp_preserved": True,
            "projection_is_external_fact": False,
            "source_evidence_mutated": False,
            "authority_transferred": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


@dataclass(frozen=True, slots=True)
class ConvertedInterval:
    source_clock_ref: str
    original_interval: TemporalInterval
    projected_interval: TemporalInterval
    clock_offset_seconds: float
    clock_uncertainty_seconds: float

    def projection(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "source_clock_ref": (
                self.source_clock_ref
            ),
            "original_interval": (
                self.original_interval.projection()
            ),
            "projected_interval": (
                self.projected_interval.projection()
            ),
            "clock_offset_seconds": float(
                self.clock_offset_seconds
            ),
            "clock_uncertainty_seconds": float(
                self.clock_uncertainty_seconds
            ),
            "uncertainty_propagated": True,
            "original_interval_preserved": True,
            "projection_is_external_fact": False,
            "source_evidence_mutated": False,
            "authority_transferred": False,
            "derived": True,
            "authoritative": False,
            "authority_effect": "none",
        }

        body["digest"] = _digest(body)
        return body


def convert_timestamp(
    value: datetime,
    *,
    source_clock_ref: str,
    original_timestamp: str,
    clock_estimate: ClockEstimate | None = None,
) -> ConvertedTimestamp:
    normalized = _utc(value)

    if clock_estimate is None:
        return ConvertedTimestamp(
            source_clock_ref=source_clock_ref,
            original_timestamp=original_timestamp,
            normalized_utc=normalized,
            projected_utc=normalized,
            clock_offset_seconds=0.0,
            uncertainty_seconds=0.0,
            correction_applied=False,
        )

    if (
        clock_estimate.source_clock_ref
        != source_clock_ref
    ):
        raise ValueError(
            "clock estimate belongs to another source clock"
        )

    projected = normalized - timedelta(
        seconds=clock_estimate.offset_seconds
    )

    return ConvertedTimestamp(
        source_clock_ref=source_clock_ref,
        original_timestamp=original_timestamp,
        normalized_utc=normalized,
        projected_utc=projected,
        clock_offset_seconds=(
            clock_estimate.offset_seconds
        ),
        uncertainty_seconds=(
            clock_estimate.uncertainty_seconds
        ),
        correction_applied=True,
    )


def convert_interval(
    interval: TemporalInterval,
    *,
    source_clock_ref: str,
    clock_estimate: ClockEstimate | None = None,
) -> ConvertedInterval:
    if clock_estimate is not None:
        if (
            clock_estimate.source_clock_ref
            != source_clock_ref
        ):
            raise ValueError(
                "clock estimate belongs to another source clock"
            )

        offset = (
            clock_estimate.offset_seconds
        )
        clock_uncertainty = (
            clock_estimate.uncertainty_seconds
        )
    else:
        offset = 0.0
        clock_uncertainty = 0.0

    def project(
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None

        return _utc(value) - timedelta(
            seconds=offset
        )

    projected = TemporalInterval(
        start=project(interval.start),
        end=project(interval.end),
        uncertainty_seconds=(
            float(
                interval.uncertainty_seconds
            )
            + float(clock_uncertainty)
        ),
    )

    return ConvertedInterval(
        source_clock_ref=source_clock_ref,
        original_interval=interval,
        projected_interval=projected,
        clock_offset_seconds=offset,
        clock_uncertainty_seconds=(
            clock_uncertainty
        ),
    )


def conversion_receipt(
    timestamp: ConvertedTimestamp,
    interval: ConvertedInterval | None = None,
) -> Mapping[str, Any]:
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "timestamp": timestamp.projection(),
        "interval": (
            interval.projection()
            if interval is not None
            else None
        ),
        "original_representation_preserved": True,
        "utc_normalization": True,
        "uncertainty_preserved": True,
        "clock_correction_is_projection": True,
        "destructive_conversion": False,
        "external_chronology_claimed": False,
        "authority_transferred": False,
        "derived": True,
        "authoritative": False,
        "authority_effect": "none",
    }

    body["digest"] = _digest(body)
    return body
