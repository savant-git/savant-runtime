from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, Form
from pathlib import Path
import shutil
import json

from avatar_forge.core.consent import parse_consent
from avatar_forge.core.paths import UPLOADS, REPORTS
from avatar_forge.sim.avatar_simulation import run_avatar_simulation

app = FastAPI(
    title="Carbon Avatar Forge",
    version="0.1.0",
)

@app.get("/health")
def health():
    return {
        "ok": True,
        "runtime": "savant-runtime",
        "exile": "carbon",
        "application": "avatar_forge",
    }

@app.post("/avatar/create")
async def create_avatar(
    photos: list[UploadFile] = File(...),
    voice: UploadFile | None = File(None),
    consent: str = Form(...)
):
    if not parse_consent(consent):
        return {
            "ok": False,
            "error": "explicit consent required"
        }

    incoming = UPLOADS / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)

    photo_paths = []

    for upload in photos:
        target = incoming / upload.filename
        with target.open("wb") as fp:
            shutil.copyfileobj(upload.file, fp)
        photo_paths.append(str(target))

    voice_path = None

    if voice is not None:
        target = incoming / voice.filename
        with target.open("wb") as fp:
            shutil.copyfileobj(voice.file, fp)
        voice_path = str(target)

    return run_avatar_simulation(
        photo_paths=photo_paths,
        voice_path=voice_path,
        consent_value=consent,
    )

@app.get("/avatar/{project_id}")
def get_avatar(project_id: str):
    packet = REPORTS / project_id / "carbon_packet.final.json"

    if not packet.exists():
        return {
            "ok": False,
            "error": "project not found",
            "project_id": project_id,
        }

    return json.loads(packet.read_text(encoding="utf-8"))
