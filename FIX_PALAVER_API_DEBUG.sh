#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
BACKEND="$ROOT/palaver_voice_backend.py"
LOG="$ROOT/palaver-voice-backend.log"

cp "$BACKEND" "$BACKEND.before_api_debug_$(date -u +%Y%m%dT%H%M%SZ)"

python3 - <<'PY'
from pathlib import Path

p = Path("/root/savant-runtime/palaver_voice_backend.py")
s = p.read_text()

s = s.replace(
'''model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")''',
'''model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")'''
)

s = s.replace(
'''        except Exception as e:
            last = str(e)

    return corrected, f"Palaver understood: {corrected}. No AI API responded. Check .env credentials."''',
'''        except Exception as e:
            last = str(e)

    return corrected, f"Palaver understood: {corrected}. No AI API responded. Last API error: {last}"'''
)

p.write_text(s)
PY

fuser -k 8787/tcp 2>/dev/null || true
nohup /root/savant-runtime/.venv_voice/bin/python "$BACKEND" > "$LOG" 2>&1 &

sleep 2

echo "=== HEALTH ==="
curl -s http://127.0.0.1:8787/api/health
echo

echo "=== TEST ==="
curl -s -X POST http://127.0.0.1:8787/api/palaver \
  -H 'Content-Type: application/json' \
  -d '{"text":"hey palaver what is mobius"}'
echo

echo "=== LOG ==="
tail -80 "$LOG"
