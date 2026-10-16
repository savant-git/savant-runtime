from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .opus_image_provider import (
    binding as image_provider,
)

from ...opus.runtime.creative_orchestration import (
    orchestrator,
)

from ...opus.runtime.creative_workflow_binding import (
    binding as workflow_binding,
)


schema = "savant://runtime/urge/creative-provider-composition/1.0.0"
owner = "exile:urge"


def compose() -> workflow_binding:
    execution = orchestrator(
        providers=(
            image_provider(),
        )
    )

    return workflow_binding(
        execution,
        provider_ids=(
            "openai-image",
        ),
    )


def execute(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    return compose()(request)
