#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"

if [ ! -f "$DB" ]; then
  echo "[ERROR] Missing DB:"
  echo "$DB"
  exit 1
fi

echo "=== FILES ==="
sqlite3 "$DB" "
select kind, count(*)
from files
where ignored=0
group by kind
order by kind;
"

echo
echo "=== CLASSIFICATIONS BY SCOPE ==="
sqlite3 "$DB" "
select scope, count(*)
from classifications
group by scope
order by scope;
"

echo
echo "=== CLASSIFICATIONS BY MOVE POLICY ==="
sqlite3 "$DB" "
select move_policy, count(*)
from classifications
group by move_policy
order by move_policy;
"

echo
echo "=== PYTHON IMPORTS ==="
sqlite3 "$DB" "
select resolution_status, count(*)
from python_imports
group by resolution_status
order by resolution_status;
"

echo
echo "=== UNRESOLVED PYTHON IMPORTS ==="
sqlite3 "$DB" "
select
  f.relpath,
  p.import_type,
  p.module,
  p.symbol,
  p.level,
  p.resolution_status,
  p.line_number
from python_imports p
join files f on f.id=p.source_file_id
where p.resolution_status != 'resolved'
order by f.relpath, p.line_number
limit 120;
"

echo
echo "=== PYTHON PARSE WARNINGS ==="
sqlite3 "$DB" "
select path, message
from validation_results
where validation_id='pass06_python_ast'
order by path
limit 80;
"
