"""Fetch the two verified variable Latin fonts and their licenses once, before build."""
from pathlib import Path
from urllib.request import Request, urlopen
import hashlib
import json
import os
import tempfile

webui = Path(__file__).resolve().parent
destination = webui / "public" / "fonts"
assets = json.loads("[{\"name\":\"exo2-latin.woff2\",\"url\":\"https://fonts.gstatic.com/s/exo2/v26/7cHmv4okm5zmbtYoK-4.woff2\",\"sha256\":\"4a259dde317e08aa5d37e6eb684e222ae833516b2a0fccba36ee5e36224f16be\",\"size\":40896},{\"name\":\"oxanium-latin.woff2\",\"url\":\"https://fonts.gstatic.com/s/oxanium/v21/RrQQboN_4yJ0JmiMe2LE0Q.woff2\",\"sha256\":\"3aa555c528430aab19bb2693dc206bab557767d3082dba66400784c9cc90cfbb\",\"size\":14044},{\"name\":\"exo2-license.txt\",\"url\":\"https://raw.githubusercontent.com/google/fonts/main/ofl/exo2/OFL.txt\",\"sha256\":\"7f95a8eeecc6904ffc81cd10cc8ebc7fcee72a67922924bf45f02dff03b88127\",\"size\":4386},{\"name\":\"oxanium-license.txt\",\"url\":\"https://raw.githubusercontent.com/google/fonts/main/ofl/oxanium/OFL.txt\",\"sha256\":\"fe17c0f2581d71b4e1ea7e636e7f4877c29223e11bb1dd1a871e8c3f2a86336b\",\"size\":4384}]")

def main():
    if not (webui / "package.json").is_file():
        raise SystemExit("Place this file in the webui-nextgen directory.")
    destination.mkdir(parents=True, exist_ok=True)
    # Fetch and verify the complete batch before changing any installed asset.
    pending = []
    for asset in assets:
        target = destination / asset["name"]
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == asset["sha256"]:
            continue
        with urlopen(Request(asset["url"], headers={"User-Agent": "savant-font-installer/1"}), timeout=25) as response:
            data = response.read(asset["size"] + 1)
        if len(data) != asset["size"] or hashlib.sha256(data).hexdigest() != asset["sha256"]:
            raise ValueError("Font asset verification failed: " + asset["name"])
        if asset["name"].endswith(".woff2") and data[:4] != b"wOF2":
            raise ValueError("Invalid WOFF2 file")
        pending.append((target, data))
    for target, data in pending:
        descriptor, temporary = tempfile.mkstemp(prefix=".savant-font-", dir=destination)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o644)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    print("Verified fonts installed:", destination)

if __name__ == "__main__":
    main()
