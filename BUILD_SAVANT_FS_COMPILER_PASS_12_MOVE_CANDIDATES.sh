#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"

python3 - <<'PY'
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"

EXILES = ROOT / "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
OBELISKS = ROOT / "ontology/obelisks"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("DELETE FROM move_candidates")

rows = cur.execute(
    """
    SELECT
        f.id,
        f.path,
        f.relpath,
        f.basename,
        f.extension,
        c.owner,
        c.scope,
        c.containment,
        c.edifice_level,
        c.authority_class,
        c.move_policy
    FROM files f
    JOIN classifications c ON c.file_id=f.id
    WHERE f.ignored=0
      AND f.kind='file'
    ORDER BY f.path
    """
).fetchall()

def proposed_target(row):
    (
        file_id,
        path,
        relpath,
        basename,
        extension,
        owner,
        scope,
        containment,
        edifice_level,
        authority_class,
        move_policy,
    ) = row

    if move_policy != "ELIGIBLE_FOR_PLANNING":
        return ""

    if containment in {
        "application_package",
        "runtime_protocol_package",
        "runtime_provider_package",
        "runtime_event_bus_package",
        "projection_engine_package",
    }:
        return ""

    if extension != "sh":
        return ""

    if scope == "all_exiles":
        return str(EXILES / "segue/authority_db/seeds" / basename)

    if scope == "all_obelisks":
        return str(OBELISKS / "segue/authority_db/seeds" / basename)

    if scope == "ontology":
        return str(OBELISKS / "segue/ontology_ops/scripts" / basename)

    if scope in {"runtime", "runtime_ops"}:
        return str(ROOT / "ops/runtime/scripts" / basename)

    if scope == "single_exile" and owner != "unknown":
        return str(EXILES / owner / "segue/scripts" / basename)

    return ""

for row in rows:
    file_id = row[0]
    src = Path(row[1])
    dst_text = proposed_target(row)

    if not dst_text:
        continue

    dst = Path(dst_text)

    reference_count = cur.execute(
        """
        SELECT count(*)
        FROM canonical_path_claims
        WHERE claimed_path=?
        """,
        (str(src),)
    ).fetchone()[0]

    shell_ref_count = cur.execute(
        """
        SELECT count(*)
        FROM shell_dependencies
        WHERE resolved_path=?
           OR target_text=?
        """,
        (str(src), str(src))
    ).fetchone()[0]

    total_refs = reference_count + shell_ref_count

    decision = "BLOCK"
    reason = "manual_review_required"
    confidence = 0

    if src == dst:
        decision = "KEEP"
        reason = "already_canonical"
        confidence = 100
    elif dst.exists():
        decision = "BLOCK"
        reason = "target_exists"
        confidence = 0
    elif total_refs > 0:
        decision = "BLOCK"
        reason = "references_require_wrapper_or_rewrite"
        confidence = 70
    else:
        decision = "CANDIDATE"
        reason = "scope_target_no_known_references_no_conflict"
        confidence = 90

    cur.execute(
        """
        INSERT INTO move_candidates
        (
            file_id,
            proposed_target,
            decision,
            reason,
            confidence,
            reference_count,
            package_risk
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_id,
            str(dst),
            decision,
            reason,
            confidence,
            total_refs,
            ""
        )
    )

con.commit()

print("[OK] pass 12 move candidates built")
for decision, count in cur.execute("""
    SELECT decision, count(*)
    FROM move_candidates
    GROUP BY decision
    ORDER BY decision
"""):
    print(decision, count)

con.close()
PY
