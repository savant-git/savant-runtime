from __future__ import annotations

from typing import Any, Dict


def authority(
    *,
    owner: str,
    source: str = "runtime",
    confidence: str = "confirmed",
    policy: str = "authority_before_inference",
    **extra: Any
) -> Dict[str, Any]:
    return {
        "owner": owner,
        "source": source,
        "confidence": confidence,
        "policy": policy,
        **extra
    }
