#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
ENVOY="$EXILES_ROOT/envoy"

mkdir -p \
  "$ENVOY/registry/location" \
  "$ENVOY/registry/accents/local" \
  "$ENVOY/runtime"

cat > "$ENVOY/registry/location/local_accent_policy.json" <<'JSON'
{
  "id": "local_accent_policy",
  "status": "active",
  "owner": "envoy",
  "purpose": "Allow Palaver default voice to approximate the user's local accent when location evidence exists.",
  "rules": [
    "Do not claim exact accent detection.",
    "Do not infer protected identity traits.",
    "Use coarse regional accent only.",
    "Prefer user-declared location over browser geolocation.",
    "Prefer browser geolocation over IP-derived location.",
    "Store confidence with every accent profile.",
    "Allow user override at all times."
  ],
  "sources_ranked": [
    "user_declared",
    "browser_geolocation",
    "ip_lookup",
    "default"
  ]
}
JSON

cat > "$ENVOY/registry/accents/local/default.json" <<'JSON'
{
  "accent_id": "local/default",
  "label": "Default Neutral",
  "region": "unknown",
  "accent": "neutral American English",
  "confidence": "low",
  "source": "default",
  "cadence": "clear, direct, measured",
  "notes": "Fallback accent when no reliable location signal exists."
}
JSON

cat > "$ENVOY/registry/accents/local/us_southeast.json" <<'JSON'
{
  "accent_id": "local/us_southeast",
  "label": "US Southeast Approximation",
  "region": "US Southeast",
  "accent": "soft Southern-influenced American English, lightly applied",
  "confidence": "medium",
  "source": "region_mapping",
  "cadence": "slightly warmer pacing, rounded vowels, not exaggerated",
  "notes": "Coarse regional approximation only."
}
JSON

cat > "$ENVOY/registry/accents/local/south_florida.json" <<'JSON'
{
  "accent_id": "local/south_florida",
  "label": "South Florida Approximation",
  "region": "South Florida",
  "accent": "South Florida American English, subtle coastal urban influence, lightly applied",
  "confidence": "medium",
  "source": "region_mapping",
  "cadence": "clean, quick, contemporary, not caricatured",
  "notes": "Coarse local approximation only."
}
JSON

cat > "$ENVOY/runtime/local_accent.py" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


ENVOY_ROOT = Path(__file__).resolve().parents[1]
ACCENTS = ENVOY_ROOT / "registry" / "accents" / "local"


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def default_accent() -> Dict[str, Any]:
    return read_json(ACCENTS / "default.json")


def resolve_local_accent(
    *,
    city: Optional[str] = None,
    region: Optional[str] = None,
    country: Optional[str] = None,
    source: str = "default"
) -> Dict[str, Any]:
    c = (city or "").lower()
    r = (region or "").lower()
    country_l = (country or "").lower()

    if "florida" in r or "fl" == r:
        if any(x in c for x in ["miami", "fort lauderdale", "hollywood", "west park", "pompano", "hialeah"]):
            row = read_json(ACCENTS / "south_florida.json")
            row["source"] = source
            return row

    if country_l in {"us", "usa", "united states", "united states of america"}:
        if any(x in r for x in ["florida", "georgia", "alabama", "mississippi", "louisiana", "south carolina", "north carolina", "tennessee"]):
            row = read_json(ACCENTS / "us_southeast.json")
            row["source"] = source
            return row

    row = default_accent()
    row["source"] = source
    return row


def voice_instruction_for_location(location: Dict[str, Any]) -> str:
    accent = resolve_local_accent(
        city=location.get("city"),
        region=location.get("region") or location.get("state"),
        country=location.get("country"),
        source=location.get("source", "unknown")
    )

    return (
        f"Local accent mode: {accent.get('label')}. "
        f"Accent: {accent.get('accent')}. "
        f"Cadence: {accent.get('cadence')}. "
        f"Confidence: {accent.get('confidence')}. "
        "Apply subtly. Do not exaggerate. Do not claim exact accent detection."
    )
PY

echo "[OK] Envoy local accent layer installed:"
find "$ENVOY/registry/location" "$ENVOY/registry/accents/local" "$ENVOY/runtime" -maxdepth 2 -type f | sort
