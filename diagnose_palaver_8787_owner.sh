#!/usr/bin/env bash
set -euo pipefail

printf '\n=== PORT 8787 OWNER ===\n'
ss -ltnp 'sport = :8787'

PID="$(
  ss -ltnp 'sport = :8787' \
  | grep -oE 'pid=[0-9]+' \
  | cut -d= -f2 \
  | head -n1
)"

printf '\nPID=%s\n' "$PID"

if [ -n "$PID" ]; then
  printf '\n=== CMDLINE ===\n'
  tr '\0' ' ' <"/proc/$PID/cmdline"
  printf '\n'

  printf '\n=== PROCESS ===\n'
  ps -fp "$PID"

  printf '\n=== CGROUP ===\n'
  cat "/proc/$PID/cgroup"
fi

printf '\n=== PALAVER SERVICES ===\n'
systemctl --no-pager --full status \
  palaver-voice-backend.service \
  2>/dev/null || true

systemctl list-units \
  --type=service \
  --all \
  --no-pager \
  | grep -i palaver || true

printf '\n=== RECENT VOICE BACKEND JOURNAL ===\n'
journalctl \
  --since '15 minutes ago' \
  --no-pager \
  -u palaver-voice-backend.service \
  | tail -100
