#!/usr/bin/env bash
set -euo pipefail

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:-/root/savant-runtime/canon-system}"

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -a "$SOURCE" "$DEST"

python3 -m venv "$DEST/.venv"
"$DEST/.venv/bin/pip" install --upgrade pip
"$DEST/.venv/bin/pip" install -r "$DEST/requirements.txt"

cat > /usr/local/bin/canonctl <<EOF
#!/usr/bin/env bash
exec "$DEST/.venv/bin/python" "$DEST/runtime/canonctl.py" "\$@"
EOF
chmod +x /usr/local/bin/canonctl

canonctl validate
canonctl project
canonctl build-db

printf 'installed: %s\n' "$DEST"
printf 'command: canonctl\n'
