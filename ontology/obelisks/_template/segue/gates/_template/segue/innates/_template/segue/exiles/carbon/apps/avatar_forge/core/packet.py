from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import uuid


@dataclass
class CarbonSimulationPacket:
    """
    Canonical Carbon simulation packet.

    Every simulation entering Carbon should eventually normalize into this
    structure before downstream simulation stages.
    """

    project_id: str
    created_at: str

    exile: str
    prodigal: str

    simulation_type: str

    consent: bool

    inputs: dict[str, Any]

    stages: dict[str, Any]

    metadata: dict[str, Any]

    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)

        destination.write_text(
            json.dumps(
                self.to_dict(),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


def new_packet(
    photo_paths: list[str],
    voice_path: str | None = None,
    consent: bool = False,
) -> CarbonSimulationPacket:

    project_id = "carbon_avatar_" + uuid.uuid4().hex[:12]

    return CarbonSimulationPacket(
        project_id=project_id,
        created_at=datetime.utcnow().isoformat() + "Z",

        exile="carbon",
        prodigal="avatar_forge",

        simulation_type="photoreal_avatar",

        consent=consent,

        inputs={
            "photos": photo_paths,
            "voice": voice_path,
        },

        stages={
            "photo_intake": None,
            "identity": None,
            "body": None,
            "textures": None,
            "voice": None,
            "rig": None,
            "simulation": None,
            "export": None,
        },

        metadata={
            "version": "0.1.0",
            "generator": "carbon.avatar_forge",
            "engine": "simulation",
        },

        status="created",
    )


def load_packet(path: Path) -> CarbonSimulationPacket:

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    return CarbonSimulationPacket(**data)


def save_packet(
    packet: CarbonSimulationPacket,
    path: Path,
) -> None:
    packet.save(path)
