from __future__ import annotations

import base64
from typing import Any, Dict

from router import execute_voice_request


def synthesize_voice_request(request: Dict[str, Any]) -> Dict[str, Any]:
    result = execute_voice_request(request)

    return {
        "ok": True,
        "provider": result.get("provider"),
        "model": result.get("model"),
        "voice": result.get("voice"),
        "mime_type": result.get("mime_type", "audio/mpeg"),
        "audio_base64": base64.b64encode(result["audio"]).decode("ascii"),
        "lineage": result.get("lineage", {})
    }
